from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import get_nyaa_client
from animedownloader_releases import Release


@dataclass
class FakeNyaaClient:
    releases: list[Release]

    async def search(self, query: str) -> list[Release]:
        assert query == "Frieren"
        return self.releases


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
        response = await client.get("/api/releases/search", params={"q": "Frieren"})

    assert response.status_code == 200
    assert response.json()["query"] == "Frieren"
    assert response.json()["items"][0]["title"] == release.title
