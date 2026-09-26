import httpx
import pytest
from animedownloader_nyaa import RSS_RESULT_LIMIT, NyaaClient


def _feed(item_count: int) -> str:
    items = "".join(
        f"""
        <item>
          <title>[ExampleSubs] Frieren - {index:02d}</title>
          <link>https://nyaa.si/download/{index}.torrent</link>
          <guid>https://nyaa.si/view/{index}</guid>
        </item>
        """
        for index in range(1, item_count + 1)
    )
    return f"<rss><channel>{items}</channel></rss>"


@pytest.mark.anyio
async def test_search_reports_when_rss_result_limit_is_reached() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            text=_feed(RSS_RESULT_LIMIT),
            request=request,
        ),
    )
    client = httpx.AsyncClient(transport=transport)

    async with NyaaClient(http_client=client) as nyaa:
        result = await nyaa.search("Frieren")

    await client.aclose()

    assert len(result.items) == RSS_RESULT_LIMIT
    assert result.result_cap_reached is True


@pytest.mark.anyio
async def test_search_does_not_report_cap_for_smaller_result_set() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            text=_feed(2),
            request=request,
        ),
    )
    client = httpx.AsyncClient(transport=transport)

    async with NyaaClient(http_client=client) as nyaa:
        result = await nyaa.search("Frieren")

    await client.aclose()

    assert len(result.items) == 2
    assert result.result_cap_reached is False
