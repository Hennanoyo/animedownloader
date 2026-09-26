from pathlib import Path

import httpx
import pytest
from animedownloader_nyaa import NyaaClient
from animedownloader_nyaa.parser import parse_rss_feed

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "nyaa_search.xml"


def test_parse_rss_feed() -> None:
    releases = parse_rss_feed(FIXTURE_PATH.read_text())

    assert len(releases) == 2
    assert releases[0].id == "https://nyaa.si/view/123456"
    assert releases[0].title == "[ExampleSubs] Frieren - 01 [1080p].mkv"
    assert releases[0].torrent_url.endswith("/123456.torrent")
    assert releases[0].seeders == 42
    assert releases[0].leechers == 3
    assert releases[0].downloads == 120
    assert releases[0].size == "1.24 GiB"
    assert releases[0].info_hash == "0123456789abcdef0123456789abcdef01234567"
    assert releases[0].published_at is not None


@pytest.mark.anyio
async def test_nyaa_client_search_uses_rss_query() -> None:
    fixture = FIXTURE_PATH.read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/"
        assert request.url.params["page"] == "rss"
        assert request.url.params["q"] == "Frieren"
        return httpx.Response(200, text=fixture)

    transport = httpx.MockTransport(handler)
    async with (
        httpx.AsyncClient(base_url="https://nyaa.si", transport=transport) as http_client,
        NyaaClient(http_client=http_client) as client,
    ):
        releases = await client.search("Frieren")

    assert len(releases.items) == 2
