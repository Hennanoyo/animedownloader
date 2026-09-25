from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from animedownloader_api.release_discovery import ReleaseDiscoveryService
from animedownloader_nyaa import NyaaError
from animedownloader_releases import Release, SearchQueryContext, build_search_queries



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
        if query == "ExampleSubs Frieren":
            return [replace(_release("[ExampleSubs] Frieren - 01 [1080p]"), id="duplicate")]
        if query == "Frieren":
            return [_release("[ExampleSubs] Frieren - 01 [1080p]")]
        if query == "ExampleSubs Frieren 1 1080p HEVC":
            raise NyaaError("specific query failed")
        return []


class EmptyScalars:
    def all(self) -> list[object]:
        return []

    def first(self) -> None:
        return None


@pytest.mark.anyio
async def test_discovery_executes_progressive_queries_and_deduplicates() -> None:
    session = MagicMock()
    session.scalars = AsyncMock(return_value=EmptyScalars())
    client = FakeNyaaClient()
    service = ReleaseDiscoveryService(session, client)

    result = await service.discover(title="Frieren", group="ExampleSubs", episode=1)

    assert result.queries == build_search_queries(
        SearchQueryContext(group="ExampleSubs", title="Frieren", episode=1)
    )
    assert client.queries == list(result.queries)
    assert len(result.items) == 1
    assert result.failed_queries == ("ExampleSubs Frieren 1 1080p HEVC",)
