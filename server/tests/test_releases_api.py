from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid7

import httpx
import pytest
from animedownloader_anime import Anime, Episode
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_nyaa_client,
    get_release_discovery_service,
    get_release_ingestion_service,
)
from animedownloader_api.release_discovery import (
    ReleaseDiscoveryItem,
    ReleaseDiscoveryResult,
)
from animedownloader_api.release_ingestion import EpisodeIngestionResult
from animedownloader_releases import (
    AnimeMatchCandidate,
    AnimeMatchResult,
    AnimeMatchStatus,
    EpisodeIngestionStatus,
    ParsedRelease,
    ParseStatus,
    Release,
)

@dataclass
class FakeNyaaClient:
    releases: list[Release]

    async def search(self, query: str) -> list[Release]:
        assert query == "Frieren"
        return self.releases


@dataclass
class FakeDiscoveryService:
    result: ReleaseDiscoveryResult

    async def discover(self, **_: object) -> ReleaseDiscoveryResult:
        return self.result


@dataclass
class FakeIngestionService:
    result: EpisodeIngestionResult

    async def ingest(self, **_: object) -> EpisodeIngestionResult:
        return self.result

    async def replace(self, **_: object) -> EpisodeIngestionResult:
        return self.result


@pytest.mark.anyio
async def test_search_releases() -> None:
    release = Release(
        source="nyaa",
        id="https://nyaa.si/view/123456",
        title="[ExampleSubs] Frieren - 01 [1080p].mkv",
        page_url="https://nyaa.si/view/123456",
        torrent_url="https://nyaa.si/download/123456.torrent",
        published_at=datetime(2026, 9, 22, 10, 20, 30, tzinfo=UTC),
        size="1.24 GiB",
        seeders=42,
        leechers=3,
        downloads=120,
        info_hash="0123456789abcdef0123456789abcdef01234567",
    )

    app = create_app()
    app.dependency_overrides[get_nyaa_client] = lambda: FakeNyaaClient([release])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/releases/search",
            params={"q": "Frieren"},
            headers={"Origin": "http://localhost:5173"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.json()["query"] == "Frieren"
    assert response.json()["items"][0]["title"] == release.title


@pytest.mark.anyio
async def test_discover_releases_returns_parsed_candidates() -> None:
    release = Release(
        source="nyaa",
        id="https://nyaa.si/view/654321",
        title="[ExampleSubs] Frieren Episode-08 [1080p].mkv",
        page_url="https://nyaa.si/view/654321",
        torrent_url="https://nyaa.si/download/654321.torrent",
        published_at=None,
        size="1.2 GiB",
        seeders=12,
        leechers=1,
        downloads=30,
        info_hash="abcdef0123456789abcdef0123456789abcdef01",
    )
    parsed = ParsedRelease(
        provider_source="nyaa",
        source_id=release.id,
        original_title=release.title,
        normalized_title=release.title.removesuffix(".mkv"),
        release_group="ExampleSubs",
        series_title="Frieren",
        episode_number=8,
        episode_title=None,
        season_number=None,
        resolution="1080p",
        source=None,
        video_codec="HEVC",
        audio_codec=None,
        bit_depth=10,
        status=ParseStatus.PARSED,
    )

    anime = Anime(
        id=uuid7(),
        title="Frieren",
        titles={"romaji": "Sousou no Frieren"},
    )
    match = AnimeMatchResult(
        status=AnimeMatchStatus.MATCHED,
        normalized_series_title="frieren",
        candidates=(
            AnimeMatchCandidate(
                anime_id=anime.id,
                title=anime.title,
                matched_titles=("Frieren",),
            ),
        ),
    )

    app = create_app()
    app.dependency_overrides[get_release_discovery_service] = lambda: FakeDiscoveryService(
        ReleaseDiscoveryResult(
            query="ExampleSubs Frieren 8",
            warnings=(),
            search_profile_version=2,
            items=(ReleaseDiscoveryItem(release=release, parsed=parsed, match=match),),
        )
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/releases/discover",
            params={"title": "Frieren", "group": "ExampleSubs", "episode": 8},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "ExampleSubs Frieren 8"
    assert payload["search_profile_version"] == 2
    assert payload["items"][0]["release"]["title"] == release.title
    assert payload["items"][0]["parsed"]["series_title"] == "Frieren"
    assert payload["items"][0]["parsed"]["episode_number"] == 8



@pytest.mark.anyio
async def test_ingest_release_returns_created_episode() -> None:
    anime_id = uuid7()
    now = datetime(2026, 9, 25, tzinfo=UTC)
    episode = Episode(
        id=uuid7(),
        anime_id=anime_id,
        episode_number=8,
        title="Episode 8",
        source="nyaa",
        source_id="https://nyaa.si/view/654321",
        source_title="[ExampleSubs] Frieren - 08 [1080p].mkv",
        source_url="https://nyaa.si/view/654321",
        torrent_url="https://nyaa.si/download/654321.torrent",
        size="1.2 GiB",
        seeders=12,
        leechers=1,
        downloads=30,
        info_hash="abcdef0123456789abcdef0123456789abcdef01",
        download_status="not_started",
        conversion_status="not_started",
        created_at=now,
        updated_at=now,
    )
    service = FakeIngestionService(
        EpisodeIngestionResult(
            status=EpisodeIngestionStatus.CREATED,
            episode=episode,
            existing_episode=None,
        ),
    )

    app = create_app()
    app.dependency_overrides[get_release_ingestion_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/releases/ingest",
            json={
                "anime_id": str(anime_id),
                "release": {
                    "source": "nyaa",
                    "id": "https://nyaa.si/view/654321",
                    "title": "[ExampleSubs] Frieren - 08 [1080p].mkv",
                    "page_url": "https://nyaa.si/view/654321",
                    "torrent_url": "https://nyaa.si/download/654321.torrent",
                    "published_at": None,
                    "size": "1.2 GiB",
                    "seeders": 12,
                    "leechers": 1,
                    "downloads": 30,
                    "info_hash": "abcdef0123456789abcdef0123456789abcdef01",
                },
                "parsed": {
                    "provider_source": "nyaa",
                    "source_id": "https://nyaa.si/view/654321",
                    "original_title": "[ExampleSubs] Frieren - 08 [1080p].mkv",
                    "normalized_title": "[ExampleSubs] Frieren - 08 [1080p]",
                    "release_group": "ExampleSubs",
                    "series_title": "Frieren",
                    "episode_number": 8,
                    "episode_title": None,
                    "season_number": None,
                    "resolution": "1080p",
                    "source": None,
                    "video_codec": "HEVC",
                    "audio_codec": None,
                    "bit_depth": 10,
                    "status": "parsed",
                    "warnings": [],
                    "failed_required_fields": [],
                    "parser_profile_version": 1,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "created"
    assert payload["episode"]["episode_number"] == 8
    assert payload["existing_episode"] is None


@pytest.mark.anyio
async def test_replace_episode_release_returns_replaced_episode() -> None:
    anime_id = uuid7()
    episode_id = uuid7()
    now = datetime(2026, 9, 26, tzinfo=UTC)
    episode = Episode(
        id=episode_id,
        anime_id=anime_id,
        episode_number=1,
        title="User title",
        source="nyaa",
        source_id="e2e-release-2",
        source_title="New release",
        source_url="https://e2e.invalid/release/2",
        torrent_url="https://e2e.invalid/download/2.torrent",
        size="1.3 GiB",
        seeders=20,
        leechers=2,
        downloads=40,
        info_hash="cccccccccccccccccccccccccccccccccccccccc",
        download_status="not_started",
        conversion_status="not_started",
        created_at=now,
        updated_at=now,
    )
    service = FakeIngestionService(
        EpisodeIngestionResult(
            status=EpisodeIngestionStatus.REPLACED,
            episode=episode,
            existing_episode=None,
        ),
    )

    app = create_app()
    app.dependency_overrides[get_release_ingestion_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            f"/api/releases/episodes/{episode_id}/replace",
            json={
                "release": {
                    "source": "nyaa",
                    "id": "e2e-release-2",
                    "title": "New release",
                    "page_url": "https://e2e.invalid/release/2",
                    "torrent_url": "https://e2e.invalid/download/2.torrent",
                    "published_at": None,
                    "size": "1.3 GiB",
                    "seeders": 20,
                    "leechers": 2,
                    "downloads": 40,
                    "info_hash": "cccccccccccccccccccccccccccccccccccccccc",
                },
                "parsed": {
                    "provider_source": "nyaa",
                    "source_id": "e2e-release-2",
                    "original_title": "New release",
                    "normalized_title": "New release",
                    "release_group": "ExampleSubs",
                    "series_title": "Frieren",
                    "episode_number": 1,
                    "episode_title": "Parsed title",
                    "season_number": None,
                    "resolution": "1080p",
                    "source": "WEB",
                    "video_codec": "HEVC",
                    "audio_codec": "AAC",
                    "bit_depth": 10,
                    "status": "parsed",
                    "warnings": [],
                    "failed_required_fields": [],
                    "parser_profile_version": 1,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "replaced"
    assert payload["episode"]["id"] == str(episode_id)
    assert payload["existing_episode"] is None
