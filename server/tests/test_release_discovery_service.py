from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from animedownloader_anime import AnimeReleasePreference
from animedownloader_api.release_discovery import ReleaseDiscoveryService
from animedownloader_nyaa import NyaaError
from animedownloader_releases import (
    AnimeMatchCandidate,
    AnimeMatchResult,
    AnimeMatchStatus,
    ParsedRelease,
    ParseStatus,
    Release,
    SearchField,
)
from animedownloader_releases.entities import ReleaseGroup


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

    async def search(self, query: str) -> list[Release]:
        self.queries.append(query)
        if query == "ExampleSubs Frieren 1 1080p HEVC":
            return [replace(_release("[ExampleSubs] Frieren - 01 [1080p][HEVC]"), id="release-1")]
        raise NyaaError("unexpected second request")


class EmptyScalars:
    def all(self) -> list[object]:
        return []

    def first(self) -> None:
        return None


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

        async def search(self, query: str) -> list[Release]:
            self.queries.append(query)
            raise NyaaError("search failed")

    client = FailingClient()
    service = ReleaseDiscoveryService(session, client)

    result = await service.discover(title="Frieren")

    assert client.queries == ["Frieren"]
    assert result.items == ()
    assert result.warnings == ("Search query failed: Frieren",)


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
