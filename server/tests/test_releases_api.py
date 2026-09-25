from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_nyaa_client,
    get_release_discovery_service,
)
from animedownloader_api.release_discovery import (
    ReleaseDiscoveryItem,
    ReleaseDiscoveryResult,
)
from animedownloader_releases import ParsedRelease, ParseStatus, Release


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

    app = create_app()
    app.dependency_overrides[get_release_discovery_service] = lambda: FakeDiscoveryService(
        ReleaseDiscoveryResult(
            queries=("ExampleSubs Frieren 8", "Frieren 8"),
            failed_queries=(),
            warnings=(),
            search_profile_version=2,
            items=(ReleaseDiscoveryItem(release=release, parsed=parsed),),
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
    assert payload["queries"] == ["ExampleSubs Frieren 8", "Frieren 8"]
    assert payload["search_profile_version"] == 2
    assert payload["items"][0]["release"]["title"] == release.title
    assert payload["items"][0]["parsed"]["series_title"] == "Frieren"
    assert payload["items"][0]["parsed"]["episode_number"] == 8
