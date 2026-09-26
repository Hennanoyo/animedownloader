from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from animedownloader_anime import Anime, AnimeReleasePreference
from animedownloader_api.release_candidates import ReleaseDiscoveryCandidateService
from animedownloader_api.release_discovery_config import ReleaseDiscoverySchedule
from animedownloader_api.release_discovery import (
    ReleaseDiscoveryQueryResult,
    ReleaseDiscoveryService,
)
from animedownloader_nyaa import NyaaError
from animedownloader_releases import (
    AnimeMatchCandidate,
    AnimeMatchResult,
    AnimeMatchStatus,
    ParsedRelease,
    ParseStatus,
    Release,
    ReleaseSearchResult,
    SearchField,
    SearchPlan,
    SearchPlanQuery,
)
from animedownloader_releases.entities import (
    ReleaseGroup,
    ReleaseSearchField,
    ReleaseSearchProfile,
)


def _release(title: str) -> Release:
    return Release(
        source="nyaa",
        id=f"https://nyaa.si/view/{abs(hash(title))}",
        title=title,
        page_url="https://nyaa.si/view/example",
        torrent_url="https://nyaa.si/download/example.torrent",
        published_at=None,
        size="1 GiB",
        seeders=10,
        leechers=1,
        downloads=2,
        info_hash=None,
    )


class FakeNyaaClient:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str) -> ReleaseSearchResult:
        self.queries.append(query)
        if query == "ExampleSubs Frieren 1 1080p HEVC":
            return ReleaseSearchResult(
                items=(
                    replace(
                        _release("[ExampleSubs] Frieren - 01 [1080p][HEVC]"),
                        id="release-1",
                    ),
                ),
            )
        raise NyaaError("unexpected second request")


class EmptyScalars:
    def all(self) -> list[object]:
        return []

    def first(self) -> None:
        return None


class EmptyExecute:
    def first(self) -> None:
        return None


class FirstScalars:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def first(self) -> object | None:
        return self.value


@pytest.mark.anyio
async def test_build_anime_search_plan_uses_saved_search_plan() -> None:
    anime = Anime(
        id=uuid7(),
        title="Frieren",
        titles={"romaji": "Sousou no Frieren"},
    )
    schedule = ReleaseDiscoverySchedule(
        anime_id=anime.id,
        search_title_source="romaji",
        search_title="Sousou no Frieren",
        search_field_order=["group", "title", "resolution", "codec", "source", "episode"],
        search_enabled_fields=["title", "resolution", "codec", "source"],
        search_group="ExampleSubs",
        search_episode=None,
        search_resolution="1080p",
        search_codec="HEVC",
        search_source="WEB-DL",
        enabled=True,
        interval_minutes=360,
        automation_mode="off",
        automation_min_ranking_score=0,
        automation_require_plan_match=True,
    )
    session = MagicMock()
    session.scalar = AsyncMock(side_effect=[anime, schedule])
    session.scalars = AsyncMock(return_value=EmptyScalars())

    service = ReleaseDiscoveryService(session, None)
    plan, profile_version = await service.build_anime_search_plan(
        anime.id,
        max_queries=3,
    )

    assert profile_version is None
    assert tuple(item.query for item in plan.queries) == (
        "Sousou no Frieren 1080p HEVC WEB-DL",
    )
    assert plan.queries[0].fields == (
        SearchField.TITLE,
        SearchField.RESOLUTION,
        SearchField.CODEC,
        SearchField.SOURCE,
    )


@pytest.mark.anyio
async def test_build_anime_search_plan_uses_alternate_titles_and_budget() -> None:
    anime = Anime(
        id=uuid7(),
        title="Frieren",
        titles={
            "romaji": "Sousou no Frieren",
            "en": "Frieren: Beyond Journey's End",
            "jp": "葬送のフリーレン",
        },
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=anime)
    session.execute = AsyncMock(return_value=EmptyExecute())

    service = ReleaseDiscoveryService(session, None)

    plan, profile_version = await service.build_anime_search_plan(
        anime.id,
        max_queries=2,
    )

    assert profile_version is None
    assert tuple(item.query for item in plan.queries) == ("Sousou no Frieren",)


@pytest.mark.anyio
async def test_build_anime_search_plan_applies_preference_and_search_profile() -> None:
    anime_id = uuid7()
    group = ReleaseGroup(
        id=uuid7(),
        name="ExampleSubs",
        slug="examplesubs",
        enabled=True,
    )
    preference = AnimeReleasePreference(
        anime_id=anime_id,
        release_group_id=group.id,
        resolution="1080p",
        video_codec="HEVC",
    )
    profile = ReleaseSearchProfile(
        id=uuid7(),
        release_group_id=group.id,
        version=4,
        status="active",
        release_group=group,
        fields=[
            ReleaseSearchField(
                id=uuid7(),
                priority=0,
                field="group",
            ),
            ReleaseSearchField(
                id=uuid7(),
                priority=1,
                field="title",
            ),
            ReleaseSearchField(
                id=uuid7(),
                priority=2,
                field="resolution",
            ),
            ReleaseSearchField(
                id=uuid7(),
                priority=3,
                field="codec",
            ),
        ],
    )
    anime = Anime(
        id=anime_id,
        title="Frieren",
        titles={
            "romaji": "Sousou no Frieren",
            "en": "Frieren: Beyond Journey's End",
            "jp": "葬送のフリーレン",
            "ko": "장송의 프리렌",
        },
    )

    session = MagicMock()
    session.scalar = AsyncMock(return_value=anime)
    session.execute = AsyncMock(
        return_value=FirstScalars((preference, group)),
    )
    session.scalars = AsyncMock(return_value=FirstScalars(profile))

    service = ReleaseDiscoveryService(session, None)

    plan, profile_version = await service.build_anime_search_plan(
        anime_id,
        max_queries=2,
    )

    assert profile_version == 4
    assert tuple(item.query for item in plan.queries) == (
        "ExampleSubs Sousou no Frieren 1080p HEVC",
        "ExampleSubs Frieren: Beyond Journey's End 1080p HEVC",
    )


@pytest.mark.anyio
async def test_discovery_executes_each_plan_query_and_deduplicates_results() -> None:
    session = MagicMock()
    session.scalars = AsyncMock(return_value=EmptyScalars())

    first = _release("[ExampleSubs] Frieren - 01 [1080p][HEVC]")
    second = replace(first, id="release-2", title="[ExampleSubs] Frieren - 02 [1080p][HEVC]")

    class MultiQueryClient:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def search(self, query: str) -> ReleaseSearchResult:
            self.queries.append(query)
            if query == "ExampleSubs Frieren":
                return ReleaseSearchResult(items=(first,))
            if query == "ExampleSubs Sousou no Frieren":
                return ReleaseSearchResult(items=(replace(first), second))
            raise NyaaError("unexpected query")

    client = MultiQueryClient()
    service = ReleaseDiscoveryService(session, client)
    plan = SearchPlan(
        queries=(
            SearchPlanQuery(
                query="ExampleSubs Frieren",
                fields=(SearchField.GROUP, SearchField.TITLE),
            ),
            SearchPlanQuery(
                query="ExampleSubs Sousou no Frieren",
                fields=(SearchField.GROUP, SearchField.TITLE),
            ),
        ),
    )

    result = await service.discover_plan(plan)

    assert client.queries == [item.query for item in plan.queries]
    assert result.queries == (
        "ExampleSubs Frieren",
        "ExampleSubs Sousou no Frieren",
    )
    assert len(result.items) == 2
    assert result.query == "ExampleSubs Frieren | ExampleSubs Sousou no Frieren"


@pytest.mark.anyio
async def test_discovery_records_query_counts_caps_and_errors() -> None:
    session = MagicMock()
    session.scalars = AsyncMock(return_value=EmptyScalars())

    class DiagnosticClient:
        async def search(self, query: str) -> ReleaseSearchResult:
            if query == "capped":
                return ReleaseSearchResult(
                    items=(_release("[ExampleSubs] Frieren - 01"),),
                    result_cap_reached=True,
                )
            raise NyaaError("provider unavailable")

    service = ReleaseDiscoveryService(session, DiagnosticClient())
    plan = SearchPlan(
        queries=(
            SearchPlanQuery(query="capped", fields=(SearchField.TITLE,)),
            SearchPlanQuery(query="failed", fields=(SearchField.TITLE,)),
        ),
    )

    result = await service.discover_plan(plan)

    assert result.query_results[0].status == "completed"
    assert result.query_results[0].result_count == 1
    assert result.query_results[0].result_cap_reached is True
    assert result.query_results[1].status == "failed"
    assert result.query_results[1].result_count == 0
    assert result.query_results[1].error_message == "provider unavailable"
    assert result.warnings == (
        "Search query may be truncated at the provider result limit: capped",
        "Search query failed: failed",
    )


@pytest.mark.anyio
async def test_discovery_records_provider_cap_signal() -> None:
    session = MagicMock()
    session.scalars = AsyncMock(return_value=EmptyScalars())

    class CappedClient:
        async def search(self, query: str) -> ReleaseSearchResult:
            return ReleaseSearchResult(
                items=(_release("[ExampleSubs] Frieren - 01"),),
                result_cap_reached=True,
            )

    service = ReleaseDiscoveryService(session, CappedClient())
    plan = SearchPlan(
        queries=(
            SearchPlanQuery(query="Frieren", fields=(SearchField.TITLE,)),
        ),
    )

    result = await service.discover_plan(plan)

    assert result.query_results == (
        ReleaseDiscoveryQueryResult(
            position=1,
            query="Frieren",
            status="completed",
            result_count=1,
            result_cap_reached=True,
        ),
    )
    assert result.warnings == (
        "Search query may be truncated at the provider result limit: Frieren",
    )


@pytest.mark.anyio
async def test_discovery_continues_when_one_plan_query_fails() -> None:
    session = MagicMock()
    session.scalars = AsyncMock(return_value=EmptyScalars())

    class PartialFailureClient:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def search(self, query: str) -> ReleaseSearchResult:
            self.queries.append(query)
            if query == "Frieren":
                raise NyaaError("search failed")
            return ReleaseSearchResult(items=(_release("[ExampleSubs] Frieren - 01"),))

    client = PartialFailureClient()
    service = ReleaseDiscoveryService(session, client)
    plan = SearchPlan(
        queries=(
            SearchPlanQuery(query="Frieren", fields=(SearchField.TITLE,)),
            SearchPlanQuery(query="ExampleSubs Frieren", fields=(SearchField.GROUP, SearchField.TITLE)),
        ),
    )

    result = await service.discover_plan(plan)

    assert client.queries == ["Frieren", "ExampleSubs Frieren"]
    assert len(result.items) == 1
    assert result.warnings == ("Search query failed: Frieren",)


@pytest.mark.anyio
async def test_discovery_executes_exactly_one_query() -> None:
    session = MagicMock()
    session.scalars = AsyncMock(return_value=EmptyScalars())
    client = FakeNyaaClient()
    service = ReleaseDiscoveryService(session, client)

    result = await service.discover(
        title="Frieren",
        group="ExampleSubs",
        episode=1,
        resolution="1080p",
        codec="HEVC",
    )

    assert result.query == "ExampleSubs Frieren 1 1080p HEVC"
    assert client.queries == [result.query]
    assert len(result.items) == 1
    assert result.warnings == ()


@pytest.mark.anyio
async def test_discovery_uses_user_selected_field_order() -> None:
    session = MagicMock()
    session.scalars = AsyncMock(return_value=EmptyScalars())
    client = FakeNyaaClient()
    service = ReleaseDiscoveryService(session, client)

    await service.discover(
        title="Frieren",
        group="ExampleSubs",
        episode=1,
        resolution="1080p",
        codec="HEVC",
        fields=(SearchField.TITLE, SearchField.GROUP, SearchField.EPISODE),
    )

    assert client.queries == ["Frieren ExampleSubs 1"]


@pytest.mark.anyio
async def test_discovery_reports_a_failed_single_query_without_retrying() -> None:
    session = MagicMock()
    session.scalars = AsyncMock(return_value=EmptyScalars())

    class FailingClient:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def search(self, query: str) -> ReleaseSearchResult:
            self.queries.append(query)
            raise NyaaError("search failed")

    client = FailingClient()
    service = ReleaseDiscoveryService(session, client)

    result = await service.discover(title="Frieren")

    assert client.queries == ["Frieren"]
    assert result.items == ()
    assert result.warnings == ("Search query failed: Frieren",)


@pytest.mark.anyio
async def test_get_schedule_returns_defaults_for_unconfigured_anime() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=None)
    service = ReleaseDiscoveryCandidateService(session)

    schedule = await service.get_schedule(uuid7())

    assert schedule.enabled is False
    assert schedule.interval_minutes == 360
    assert schedule.next_run_at is None


def test_rank_release_uses_only_matching_anime_and_preference_fields() -> None:
    anime_id = __import__("uuid").uuid7()
    group = ReleaseGroup(
        name="ExampleSubs",
        slug="examplesubs",
        enabled=True,
    )
    group.id = __import__("uuid").uuid7()
    preference = AnimeReleasePreference(
        anime_id=anime_id,
        release_group_id=group.id,
        resolution="1080p",
        video_codec="HEVC",
        source="WEB",
    )
    match = AnimeMatchResult(
        status=AnimeMatchStatus.MATCHED,
        normalized_series_title="frieren",
        candidates=(
            AnimeMatchCandidate(
                anime_id=anime_id,
                title="Frieren",
                matched_titles=("Frieren",),
            ),
        ),
    )
    parsed = ParsedRelease(
        provider_source="nyaa",
        source_id="release-1",
        original_title="[ExampleSubs] Frieren - 01 [1080p][HEVC]",
        normalized_title="frieren",
        release_group="ExampleSubs",
        series_title="Frieren",
        episode_number=1,
        episode_title=None,
        season_number=None,
        resolution="1080p",
        source="WEB",
        video_codec="HEVC",
        audio_codec=None,
        bit_depth=10,
        status=ParseStatus.PARSED,
    )

    ranking = ReleaseDiscoveryService.rank_release(
        parsed,
        match,
        (preference, group),
    )

    assert ranking.score == 160
    assert ranking.reasons == (
        "Preferred release group",
        "Preferred resolution",
        "Preferred video codec",
        "Preferred source",
    )
