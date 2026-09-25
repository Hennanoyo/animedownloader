from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from animedownloader_api.release_discovery import ReleaseDiscoveryService
from animedownloader_nyaa import NyaaError
from animedownloader_releases import Release, SearchQueryContext, build_search_queries

from .test_release_parser import make_release


class FakeNyaaClient:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str) -> list[Release]:
        self.queries.append(query)
        if query == "ExampleSubs Frieren":
            return [replace(make_release("[ExampleSubs] Frieren - 01 [1080p]"), id="duplicate")]
        if query == "Frieren":
            return [make_release("[ExampleSubs] Frieren - 01 [1080p]")]
        if query == "ExampleSubs Frieren 8 1080p HEVC":
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
    assert result.failed_queries == ("ExampleSubs Frieren 8 1080p HEVC",)
