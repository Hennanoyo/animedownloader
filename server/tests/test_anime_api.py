from datetime import UTC, datetime, time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_anime import AnimeNotFoundError, AnimeService, DuplicateEpisodeError
from animedownloader_anime.models import Anime, Episode
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import get_anime_service


def make_anime() -> Anime:
    anime_id = uuid7()
    now = datetime(2026, 9, 23, tzinfo=UTC)
    episode = Episode(
        id=uuid7(),
        anime_id=anime_id,
        episode_number=1,
        title="Frieren - 01",
        source="nyaa",
        source_id="123456",
        source_title="[ExampleSubs] Frieren - 01 [1080p].mkv",
        source_url="https://nyaa.si/view/123456",
        torrent_url="https://nyaa.si/download/123456.torrent",
        size="1.24 GiB",
        seeders=42,
        leechers=3,
        downloads=120,
        info_hash="0123456789abcdef0123456789abcdef01234567",
        download_status="not_started",
        conversion_status="not_started",
        created_at=now,
        updated_at=now,
    )
    anime = Anime(
        id=anime_id,
        title="Frieren: Beyond Journey's End",
        year=2026,
        season="fall",
        weekday="friday",
        air_time=time(23),
        timezone="Asia/Tokyo",
        created_at=now,
        updated_at=now,
    )
    anime.episodes.append(episode)
    return anime


@pytest.mark.anyio
async def test_create_anime() -> None:
    service = MagicMock(spec=AnimeService)
    service.create_anime = AsyncMock(return_value=make_anime())

    app = create_app()
    app.dependency_overrides[get_anime_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/animes",
            json={
                "title": "Frieren: Beyond Journey's End",
                "year": 2026,
                "season": "fall",
                "weekday": "friday",
                "air_time": "23:00:00",
                "timezone": "Asia/Tokyo",
                "episodes": [
                    {
                        "episode_number": 1,
                        "title": "Frieren - 01",
                        "source": "nyaa",
                        "source_id": "123456",
                        "source_title": "[ExampleSubs] Frieren - 01 [1080p].mkv",
                        "source_url": "https://nyaa.si/view/123456",
                        "torrent_url": "https://nyaa.si/download/123456.torrent",
                        "size": "1.24 GiB",
                        "seeders": 42,
                        "leechers": 3,
                        "downloads": 120,
                        "info_hash": "0123456789abcdef0123456789abcdef01234567",
                    }
                ],
            },
        )

    assert response.status_code == 201
    assert response.json()["episodes"][0]["download_status"] == "not_started"
    service.create_anime.assert_awaited_once()


@pytest.mark.anyio
async def test_missing_anime_is_404() -> None:
    service = MagicMock(spec=AnimeService)
    service.get_anime = AsyncMock(side_effect=AnimeNotFoundError(uuid7()))

    app = create_app()
    app.dependency_overrides[get_anime_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/animes/" + str(uuid7()))

    assert response.status_code == 404


@pytest.mark.anyio
async def test_duplicate_episode_is_409() -> None:
    service = MagicMock(spec=AnimeService)
    service.create_episode = AsyncMock(side_effect=DuplicateEpisodeError(1))

    app = create_app()
    app.dependency_overrides[get_anime_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/animes/" + str(uuid7()) + "/episodes",
            json={
                "episode_number": 1,
                "title": "Duplicate",
                "source": "nyaa",
                "torrent_url": "https://nyaa.si/download/123456.torrent",
            },
        )

    assert response.status_code == 409
