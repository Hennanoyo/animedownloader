from __future__ import annotations

import asyncio
from dataclasses import dataclass

from animedownloader_nyaa import NyaaClient, NyaaError
from animedownloader_releases import (
    ParsedRelease,
    ParserField,
    ParserProfileSpec,
    ParserRuleSpec,
    ParserTransform,
    Release,
    ReleaseGroup,
    ReleaseParserProfile,
    ReleaseSearchProfile,
    SearchProfileSpec,
    SearchQueryContext,
    SearchTemplateSpec,
    apply_parser_profile,
    build_search_queries,
    merge_releases,
    normalize_release_group_slug,
    parse_release,
    ParserProfileStatus,
    SearchProfileStatus,
)
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload



@dataclass(frozen=True, slots=True)
class ReleaseDiscoveryItem:
    release: Release
    parsed: ParsedRelease


@dataclass(frozen=True, slots=True)
class ReleaseDiscoveryResult:
    queries: tuple[str, ...]
    failed_queries: tuple[str, ...]
    warnings: tuple[str, ...]
    search_profile_version: int | None
    items: tuple[ReleaseDiscoveryItem, ...]


class ReleaseDiscoveryService:
    def __init__(
        self,
        session: AsyncSession,
        client: NyaaClient,
    ) -> None:
        self._session = session
        self._client = client

    async def discover(
        self,
        *,
        title: str,
        group: str | None = None,
        episode: int | None = None,
        resolution: str | None = None,
        codec: str | None = None,
    ) -> ReleaseDiscoveryResult:
        context = SearchQueryContext(
            group=group,
            title=title,
            episode=episode,
            resolution=resolution,
            codec=codec,
        )
        search_profile = await self._load_search_profile(group)
        search_spec = self._to_search_profile_spec(search_profile) if search_profile else None
        queries = build_search_queries(context, search_spec)

        responses = await asyncio.gather(
            *(self._search(query) for query in queries),
        )

        failed_queries = tuple(
            query for query, _releases, failed in responses if failed
        )
        merged = merge_releases(
            releases
            for _, releases, _ in responses
        )

        parser_profiles = await self._load_parser_profiles()
        parser_map: dict[str, ParserProfileSpec] = {}
        for profile in parser_profiles:
            spec = self._to_parser_profile_spec(profile)
            parser_map[normalize_release_group_slug(spec.release_group)] = spec
            parser_map[spec.release_group.casefold()] = spec

        warnings: list[str] = []
        if failed_queries:
            warnings.extend(
                f"Search query failed and was skipped: {query}"
                for query in failed_queries
            )

        items: list[ReleaseDiscoveryItem] = []
        for release in merged:
            try:
                parsed = parse_release(release)
                if parsed.release_group:
                    profile = parser_map.get(
                        normalize_release_group_slug(parsed.release_group),
                    ) or parser_map.get(parsed.release_group.casefold())
                    if profile is not None:
                        parsed = apply_parser_profile(parsed, profile)
                items.append(ReleaseDiscoveryItem(release=release, parsed=parsed))
            except ValueError as exc:
                warnings.append(
                    f"Release could not be parsed and was skipped: {release.title}: {exc}",
                )

        return ReleaseDiscoveryResult(
            queries=queries,
            failed_queries=failed_queries,
            warnings=tuple(warnings),
            search_profile_version=(
                search_profile.version if search_profile is not None else None
            ),
            items=tuple(items),
        )

    async def _search(
        self,
        query: str,
    ) -> tuple[str, tuple[Release, ...], bool]:
        try:
            releases = await self._client.search(query)
        except NyaaError:
            return query, (), True
        return query, tuple(releases), False

    async def _load_search_profile(
        self,
        group: str | None,
    ) -> ReleaseSearchProfile | None:
        if not group:
            return None

        normalized_slug = normalize_release_group_slug(group)
        result = await self._session.scalars(
            select(ReleaseSearchProfile)
            .join(ReleaseGroup)
            .where(
                ReleaseGroup.enabled.is_(True),
                ReleaseSearchProfile.status == SearchProfileStatus.ACTIVE.value,
                or_(
                    ReleaseGroup.slug == normalized_slug,
                    func.lower(ReleaseGroup.name) == group.casefold(),
                ),
            )
            .options(
                selectinload(ReleaseSearchProfile.templates),
            )
        )
        return result.first()

    async def _load_parser_profiles(self) -> list[ReleaseParserProfile]:
        result = await self._session.scalars(
            select(ReleaseParserProfile)
            .join(ReleaseGroup)
            .where(
                ReleaseGroup.enabled.is_(True),
                ReleaseParserProfile.status == ParserProfileStatus.ACTIVE.value,
            )
            .options(
                selectinload(ReleaseParserProfile.rules),
                selectinload(ReleaseParserProfile.release_group),
            )
        )
        return list(result.all())

    @staticmethod
    def _to_search_profile_spec(
        profile: ReleaseSearchProfile,
    ) -> SearchProfileSpec:
        return SearchProfileSpec(
            release_group=profile.release_group.name,
            version=profile.version,
            templates=tuple(
                SearchTemplateSpec(
                    template=item.template,
                    priority=item.priority,
                )
                for item in profile.templates
            ),
        )

    @staticmethod
    def _to_parser_profile_spec(
        profile: ReleaseParserProfile,
    ) -> ParserProfileSpec:
        return ParserProfileSpec(
            release_group=profile.release_group.name,
            version=profile.version,
            rules=tuple(
                ParserRuleSpec(
                    field=ParserField(item.field),
                    pattern=item.pattern,
                    priority=item.priority,
                    required=item.required,
                    flags=item.flags,
                    transform=ParserTransform(item.transform),
                )
                for item in profile.rules
            ),
        )
