from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from animedownloader_anime import Anime, AnimeReleasePreference
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
    ReleaseSearchResult,
    SearchField,
    SearchPlan,
    SearchProfileSpec,
    SearchProfileStatus,
    SearchQueryContext,
    apply_parser_profile,
    build_search_plan,
    merge_releases,
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
class ReleaseRanking:
    score: int
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReleaseDiscoveryItem:
    release: Release
    parsed: ParsedRelease
    match: AnimeMatchResult
    ranking: ReleaseRanking


@dataclass(frozen=True, slots=True)
class ReleaseDiscoveryQueryResult:
    position: int
    query: str
    status: str
    result_count: int
    result_cap_reached: bool
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ReleaseDiscoveryResult:
    queries: tuple[str, ...]
    query_results: tuple[ReleaseDiscoveryQueryResult, ...] = ()
    warnings: tuple[str, ...]
    search_profile_version: int | None
    items: tuple[ReleaseDiscoveryItem, ...]

    @property
    def query(self) -> str:
        if not self.queries:
            return ""
        rendered = " | ".join(self.queries)
        return rendered if len(rendered) <= 500 else rendered[:497] + "..."


class ReleaseDiscoveryService:
    def __init__(
        self,
        session: AsyncSession,
        client: ReleaseSearchClient | None,
    ) -> None:
        self._session = session
        self._client = client

    async def discover(
        self,
        *,
        title: str,
        anime_id: UUID | None = None,
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
        plan = build_search_plan(
            (context,),
            profile=search_spec,
            fields=fields,
            max_queries=1,
        )
        if not plan.queries:
            raise ValueError("at least one non-empty search field is required")

        return await self.discover_plan(
            plan,
            anime_id=anime_id,
            search_profile_version=search_profile.version if search_profile else None,
        )

    async def build_anime_search_plan(
        self,
        anime_id: UUID,
        *,
        max_queries: int = 3,
    ) -> tuple[SearchPlan, int | None]:
        anime = await self._session.scalar(
            select(Anime).where(Anime.id == anime_id),
        )
        if anime is None:
            raise ValueError(f"anime not found: {anime_id}")

        preference = await self._load_release_preference(anime_id)
        group = None
        resolution = None
        codec = None
        if preference is not None:
            settings, preferred_group = preference
            if preferred_group is not None and preferred_group.enabled:
                group = preferred_group.name
            resolution = settings.resolution
            codec = settings.video_codec

        titles: list[str] = []
        for key in ("romaji", "en", "jp", "ko"):
            value = anime.titles.get(key)
            if value and value.strip() and value.strip() not in titles:
                titles.append(value.strip())
        if anime.title.strip() and anime.title.strip() not in titles:
            titles.append(anime.title.strip())

        search_profile = await self._load_search_profile(group)
        search_spec = self._to_search_profile_spec(search_profile) if search_profile else None
        contexts = tuple(
            SearchQueryContext(
                group=group,
                title=title,
                resolution=resolution,
                codec=codec,
            )
            for title in titles
        )
        plan = build_search_plan(
            contexts,
            profile=search_spec,
            max_queries=max_queries,
        )
        if not plan.queries:
            raise ValueError(f"Anime has no usable search title: {anime_id}")

        return plan, search_profile.version if search_profile else None

    async def discover_plan(
        self,
        plan: SearchPlan,
        *,
        anime_id: UUID | None = None,
        search_profile_version: int | None = None,
    ) -> ReleaseDiscoveryResult:
        if not plan.queries:
            raise ValueError("search plan must contain at least one query")

        if self._client is None:
            raise RuntimeError("provider client is required to execute a search plan")

        release_batches: list[tuple[Release, ...]] = []
        warnings: list[str] = []
        query_results: list[ReleaseDiscoveryQueryResult] = []
        for position, plan_query in enumerate(plan.queries, start=1):
            try:
                search_result: ReleaseSearchResult = await self._client.search(
                    plan_query.query,
                )
                release_batches.append(search_result.items)
                query_results.append(
                    ReleaseDiscoveryQueryResult(
                        position=position,
                        query=plan_query.query,
                        status="completed",
                        result_count=len(search_result.items),
                        result_cap_reached=search_result.result_cap_reached,
                    ),
                )
                if search_result.result_cap_reached:
                    warnings.append(
                        "Search query may be truncated at the provider result limit: "
                        f"{plan_query.query}",
                    )
            except NyaaError as exc:
                warnings.append(f"Search query failed: {plan_query.query}")
                query_results.append(
                    ReleaseDiscoveryQueryResult(
                        position=position,
                        query=plan_query.query,
                        status="failed",
                        result_count=0,
                        result_cap_reached=False,
                        error_message=str(exc)[:2000],
                    ),
                )

        releases = merge_releases(release_batches)

        preference = await self._load_release_preference(anime_id)
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
                match = anime_matcher.match(parsed)
                items.append(
                    ReleaseDiscoveryItem(
                        release=release,
                        parsed=parsed,
                        match=match,
                        ranking=self.rank_release(
                            parsed,
                            match,
                            preference,
                        ),
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

        if preference is not None:
            items.sort(
                key=lambda item: (
                    -item.ranking.score,
                    0 if item.parsed.status.value == "parsed" else 1,
                    -(item.release.seeders or 0),
                    item.release.title.casefold(),
                ),
            )

        return ReleaseDiscoveryResult(
            queries=tuple(query.query for query in plan.queries),
            query_results=tuple(query_results),
            warnings=tuple(warnings),
            search_profile_version=search_profile_version,
            items=tuple(items),
        )

    async def _load_release_preference(
        self,
        anime_id: UUID | None,
    ) -> tuple[AnimeReleasePreference, ReleaseGroup | None] | None:
        if anime_id is None:
            return None

        result = await self._session.execute(
            select(AnimeReleasePreference, ReleaseGroup)
            .outerjoin(
                ReleaseGroup,
                ReleaseGroup.id == AnimeReleasePreference.release_group_id,
            )
            .where(AnimeReleasePreference.anime_id == anime_id)
        )
        row = result.first()
        if row is None:
            return None
        preference, group = row
        if group is None or not group.enabled:
            return preference, group

        return preference, group

    @staticmethod
    def rank_release(
        parsed: ParsedRelease,
        match: AnimeMatchResult,
        preference: tuple[AnimeReleasePreference, ReleaseGroup | None] | None,
    ) -> ReleaseRanking:
        if preference is None:
            return ReleaseRanking(score=0)

        settings, preferred_group = preference
        if not any(
            candidate.anime_id == settings.anime_id for candidate in match.candidates
        ):
            return ReleaseRanking(score=0, reasons=("Does not match this Anime",))

        score = 0
        reasons: list[str] = []
        if (
            preferred_group is not None
            and preferred_group.enabled
            and parsed.release_group
            and normalize_release_group_slug(parsed.release_group)
            == preferred_group.slug
        ):
            score += 100
            reasons.append("Preferred release group")

        if (
            settings.resolution
            and parsed.resolution
            and parsed.resolution.casefold() == settings.resolution.casefold()
        ):
            score += 30
            reasons.append("Preferred resolution")

        if (
            settings.video_codec
            and parsed.video_codec
            and parsed.video_codec.casefold() == settings.video_codec.casefold()
        ):
            score += 20
            reasons.append("Preferred video codec")

        if (
            settings.source
            and parsed.source
            and parsed.source.casefold() == settings.source.casefold()
        ):
            score += 10
            reasons.append("Preferred source")

        return ReleaseRanking(score=score, reasons=tuple(reasons))

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
