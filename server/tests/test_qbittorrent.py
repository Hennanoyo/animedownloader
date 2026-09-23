import httpx
import pytest
from animedownloader_qbittorrent import (
    QBittorrentAddError,
    QBittorrentAPIError,
    QBittorrentClient,
)
from animedownloader_torrent import TorrentStatus


def make_client(handler: httpx.MockTransport) -> QBittorrentClient:
    http_client = httpx.AsyncClient(transport=handler)
    return QBittorrentClient(
        "http://qbittorrent:8080",
        "qbt_test_key",
        http_client=http_client,
    )


@pytest.mark.anyio
async def test_add_torrent() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = request.read()
        return httpx.Response(200, text="Ok.")

    async with make_client(httpx.MockTransport(handler)) as client:
        await client.add(
            "https://example.com/episode.torrent",
            save_path="/data/downloads",
            tags=("animedownloader:job-123",),
        )

    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v2/torrents/add"
    assert captured["authorization"] == "Bearer qbt_test_key"
    assert b"urls=https%3A%2F%2Fexample.com%2Fepisode.torrent" in captured["body"]  # type: ignore[operator]
    assert b"savepath=%2Fdata%2Fdownloads" in captured["body"]  # type: ignore[operator]
    assert b"tags=animedownloader%3Ajob-123" in captured["body"]  # type: ignore[operator]


@pytest.mark.anyio
async def test_add_torrent_pending() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            202,
            json={
                "added_torrent_ids": [],
                "failure_count": 0,
                "pending_count": 1,
                "success_count": 0,
            },
        )

    async with make_client(httpx.MockTransport(handler)) as client:
        await client.add(
            "magnet:?xt=urn:btih:example",
            save_path="/data/downloads",
            tags=("animedownloader:job-123",),
        )


@pytest.mark.anyio
async def test_add_torrent_failure() -> None:
    response_body: dict[str, object] = {
        "added_torrent_ids": [],
        "failure_count": 1,
        "pending_count": 0,
        "success_count": 0,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_body)

    async with make_client(httpx.MockTransport(handler)) as client:
        with pytest.raises(QBittorrentAddError, match="failure_count"):
            await client.add(
                "https://example.com/episode.torrent",
                save_path="/data/downloads",
            )


@pytest.mark.anyio
async def test_get_torrent() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/torrents/info"
        assert request.url.params["hashes"] == "abc123"
        return httpx.Response(
            200,
            json=[
                {
                    "hash": "abc123",
                    "name": "Episode One",
                    "state": "downloading",
                    "progress": 0.25,
                    "completed": 250,
                    "size": 1000,
                    "save_path": "/data/downloads",
                    "tags": "animedownloader:job-123",
                }
            ],
        )

    async with make_client(httpx.MockTransport(handler)) as client:
        torrent = await client.get("abc123")

    assert torrent is not None
    assert torrent.id == "abc123"
    assert torrent.status is TorrentStatus.DOWNLOADING
    assert torrent.progress == 0.25
    assert torrent.downloaded_bytes == 250
    assert torrent.total_bytes == 1000
    assert torrent.save_path == "/data/downloads"
    assert torrent.tags == frozenset({"animedownloader:job-123"})


@pytest.mark.anyio
async def test_find_by_tag_returns_latest_match() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/torrents/info"
        assert request.url.params["tag"] == "animedownloader:job-123"
        assert request.url.params["sort"] == "added_on"
        assert request.url.params["reverse"] == "true"
        assert request.url.params["limit"] == "1"
        return httpx.Response(
            200,
            json=[
                {
                    "hash": "abc123",
                    "name": "Episode One",
                    "state": "stalledDL",
                    "progress": 0.5,
                    "completed": 500,
                    "size": 1000,
                    "save_path": "/data/downloads",
                    "tags": "animedownloader:job-123,anime",
                }
            ],
        )

    async with make_client(httpx.MockTransport(handler)) as client:
        torrent = await client.find_by_tag("animedownloader:job-123")

    assert torrent is not None
    assert torrent.status is TorrentStatus.STALLED
    assert torrent.tags == frozenset({"animedownloader:job-123", "anime"})


@pytest.mark.anyio
async def test_missing_torrent_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    async with make_client(httpx.MockTransport(handler)) as client:
        assert await client.get("missing") is None


@pytest.mark.anyio
async def test_qbittorrent_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="error")

    async with make_client(httpx.MockTransport(handler)) as client:
        with pytest.raises(QBittorrentAPIError):
            await client.get("abc123")


@pytest.mark.anyio
async def test_qbittorrent_invalid_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"hash": "abc123"})

    async with make_client(httpx.MockTransport(handler)) as client:
        with pytest.raises(QBittorrentAPIError):
            await client.get("abc123")


@pytest.mark.anyio
async def test_pause_torrent() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = request.read()
        return httpx.Response(200, text="Ok.")

    async with make_client(httpx.MockTransport(handler)) as client:
        await client.pause("abc123")

    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v2/torrents/pause"
    assert b"hashes=abc123" in captured["body"]  # type: ignore[operator]


@pytest.mark.anyio
async def test_resume_torrent() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = request.read()
        return httpx.Response(200, text="Ok.")

    async with make_client(httpx.MockTransport(handler)) as client:
        await client.resume("abc123")

    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v2/torrents/resume"
    assert b"hashes=abc123" in captured["body"]  # type: ignore[operator]
