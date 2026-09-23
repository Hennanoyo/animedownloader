from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid7

import httpx
import pytest
from animedownloader_anime import AnimeService, Episode
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_anime_service,
    get_media_asset_service,
)
from animedownloader_api.schemas import MediaAssetResponse
from animedownloader_media_asset import MediaAsset, MediaAssetService


def make_asset(episode_id: UUID) -> MediaAsset:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    return MediaAsset(
        id=uuid7(),
        episode_id=episode_id,
        processing_job_id=uuid7(),
        path="/downloads/example/episode.mkv",
        format_name="matroska,webm",
        duration_seconds=60.0,
        size_bytes=1024,
        video_codec="hevc",
        audio_codec="aac",
        width=1920,
        height=1080,
        frame_rate="24000/1001",
        metadata_updated_at=now,
        created_at=now,
        updated_at=now,
    )


def make_episode(episode_id: UUID) -> Episode:
    return Episode(
        id=episode_id,
        anime_id=uuid7(),
        episode_number=1,
        title="Episode One",
        source="nyaa",
        source_id="ci-1",
        source_title="[CI] Episode One",
        source_url="https://nyaa.si/view/ci-1",
        torrent_url="https://nyaa.si/download/ci-1.torrent",
        size="1 GiB",
        seeders=10,
        leechers=2,
        downloads=30,
        info_hash="0123456789abcdef0123456789abcdef01234567",
        download_status="not_started",
        conversion_status="not_started",
    )


@pytest.mark.anyio
async def test_get_episode_media_returns_asset() -> None:
    episode_id = uuid7()
    anime_service = MagicMock(spec=AnimeService)
    media_service = MagicMock(spec=MediaAssetService)
    episode = make_episode(episode_id)
    asset = make_asset(episode_id)

    anime_service.get_episode = AsyncMock(return_value=episode)
    media_service.get_for_episode = AsyncMock(return_value=asset)

    app = create_app()
    app.dependency_overrides[get_anime_service] = lambda: anime_service
    app.dependency_overrides[get_media_asset_service] = lambda: media_service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/api/episodes/{episode_id}/media")

    assert response.status_code == 200
    payload = MediaAssetResponse.model_validate(response.json())
    assert payload.episode_id == episode_id
    assert payload.format_name == "matroska,webm"
    assert payload.duration_seconds == 60.0
    assert payload.size_bytes == 1024
    assert payload.video_codec == "hevc"
    assert payload.audio_codec == "aac"
    assert payload.width == 1920
    assert payload.height == 1080
    assert payload.frame_rate == "24000/1001"
    assert payload.metadata_updated_at == asset.metadata_updated_at
    anime_service.get_episode.assert_awaited_once_with(episode_id)
    media_service.get_for_episode.assert_awaited_once_with(episode_id)


@pytest.mark.anyio
async def test_get_episode_media_returns_null_when_asset_is_missing() -> None:
    episode_id = uuid7()
    anime_service = MagicMock(spec=AnimeService)
    media_service = MagicMock(spec=MediaAssetService)
    anime_service.get_episode = AsyncMock(return_value=make_episode(episode_id))
    media_service.get_for_episode = AsyncMock(return_value=None)

    app = create_app()
    app.dependency_overrides[get_anime_service] = lambda: anime_service
    app.dependency_overrides[get_media_asset_service] = lambda: media_service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(f"/api/episodes/{episode_id}/media")

    assert response.status_code == 200
    assert response.json() is None
