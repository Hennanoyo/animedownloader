from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from animedownloader_anime import Anime
from animedownloader_nyaa import NyaaError
from animedownloader_releases import (
    AnimeMatchResult,
    ParsedRelease,
    ParserField,
    ParserProfileSpec,
    ParserProfileStatus,
    ParserRuleSpec,
    ParserTransform,
    Release,
    ReleaseGroup,
    ReleaseParserProfile,
    ReleaseProfileService,
    ReleaseSearchProfile,
    SearchField,
    SearchProfileSpec,
    SearchProfileStatus,
    SearchQueryContext,
    apply_parser_profile,
    build_search_query,
    normalize_release_group_slug,
    parse_release,
)
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .release_matching import AnimeMatcher



class ReleaseSearchClient(Protocol):
    async def search(self, query: str) -> list[Release]:
        ...


@dataclass(frozen=True, slots=True)
class ReleaseDiscoveryItem:
    release: Release
    parsed: ParsedRelease
    match: AnimeMatchResult


@dataclass(frozen=True, slots=True)
class ReleaseDiscoveryResult:
    query: str
    warnings: tuple[str, ...]
    search_profile_version: int | None
    items: tuple[ReleaseDiscoveryItem, ...]


class ReleaseDiscoveryService:
    def __init__(
        self,
        session: AsyncSession,
        client: ReleaseSearchClient,
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
        fields: tuple[SearchField, ...] | None = None,
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
        query = build_search_query(context, search_spec, fields=fields)
        if query is None:
            raise ValueError("at least one non-empty search field is required")

        try:
            releases = tuple(await self._client.search(query))
        except NyaaError:
            return ReleaseDiscoveryResult(
                query=query,
                warnings=(f"Search query failed: {query}",),
                search_profile_version=search_profile.version if search_profile else None,
                items=(),
            )

        parser_profiles = await self._load_parser_profiles()
        parser_map: dict[str, tuple[ReleaseParserProfile, ParserProfileSpec]] = {}
        for profile in parser_profiles:
            spec = self._to_parser_profile_spec(profile)
            parser_map[normalize_release_group_slug(spec.release_group)] = (profile, spec)
            parser_map[spec.release_group.casefold()] = (profile, spec)

        anime_result = await self._session.scalars(
            select(Anime).order_by(Anime.id),
        )
        anime_matcher = AnimeMatcher(anime_result.all())

        warnings: list[str] = []
        observed_results: dict[
            UUID, tuple[UUID, list[tuple[Release, ParsedRelease]]]
        ] = {}

        items: list[ReleaseDiscoveryItem] = []
        for release in releases:
            try:
                parsed = parse_release(release)
                if parsed.release_group:
                    profile_data = parser_map.get(
                        normalize_release_group_slug(parsed.release_group),
                    ) or parser_map.get(parsed.release_group.casefold())
                    if profile_data is not None:
                        profile, profile_spec = profile_data
                        parsed = apply_parser_profile(parsed, profile_spec)
                        group_observations = observed_results.setdefault(
                            profile.id,
                            (profile.release_group_id, []),
                        )
                        group_observations[1].append((release, parsed))
                items.append(
                ReleaseDiscoveryItem(
                    release=release,
                    parsed=parsed,
                    match=anime_matcher.match(parsed),
                ),
            )
            except ValueError as exc:
                warnings.append(
                    f"Release could not be parsed and was skipped: {release.title}: {exc}",
                )

        if observed_results:
            await ReleaseProfileService(self._session).record_parse_results(
                {
                    profile_id: (group_id, tuple(observations))
                    for profile_id, (group_id, observations) in observed_results.items()
                },
            )

        return ReleaseDiscoveryResult(
            query=query,
            warnings=tuple(warnings),
            search_profile_version=(
                search_profile.version if search_profile is not None else None
            ),
            items=tuple(items),
        )

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
                selectinload(ReleaseSearchProfile.fields),
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
            fields=tuple(SearchField(item.field) for item in profile.fields),
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
