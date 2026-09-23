from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_anime_service,
    get_media_asset_service,
    get_media_transcoding_job_service,
    get_media_variant_service,
)
from animedownloader_anime import AnimeService
from animedownloader_media_asset import MediaAsset, MediaAssetService
from animedownloader_media_processing import (
    MediaTranscodingJob,
    MediaTranscodingJobService,
    MediaTranscodingJobStatus,
    MediaVariant,
    MediaVariantKind,
    MediaVariantStatus,
)


def make_client(anime_service, asset_service, variant_service, job_service):
    app = create_app()
    app.dependency_overrides[get_anime_service] = lambda: anime_service
    app.dependency_overrides[get_media_asset_service] = lambda: asset_service
    app.dependency_overrides[get_media_variant_service] = lambda: variant_service
    app.dependency_overrides[get_media_transcoding_job_service] = lambda: job_service
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def make_asset() -> MediaAsset:
    now = datetime(2026, 9, 24, tzinfo=UTC)
    return MediaAsset(
        id=uuid7(),
        episode_id=uuid7(),
        processing_job_id=uuid7(),
        path="/downloads/source.mkv",
        metadata_updated_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_get_episode_playable_media_reports_current_variant() -> None:
    asset = make_asset()
    variant = MediaVariant(
        id=uuid7(),
        media_asset_id=asset.id,
        kind=MediaVariantKind.PLAYABLE.value,
        status=MediaVariantStatus.COMPLETED.value,
        source_path=asset.path,
        source_metadata_updated_at=asset.metadata_updated_at,
        path="/data/media/playable/asset.mp4",
        format_name="mov,mp4,m4a,3gp,3g2,mj2",
        duration_seconds=60.0,
        size_bytes=100,
        video_codec="hevc",
        audio_codec="aac",
        width=1920,
        height=1080,
        frame_rate="24/1",
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )

    anime_service = MagicMock(spec=AnimeService)
    anime_service.get_episode = AsyncMock()
    asset_service = MagicMock(spec=MediaAssetService)
    asset_service.get_for_episode = AsyncMock(return_value=asset)
    variant_service = MagicMock()
    variant_service.get_playable_variant = AsyncMock(return_value=variant)
    job_service = MagicMock(spec=MediaTranscodingJobService)

    async with make_client(anime_service, asset_service, variant_service, job_service) as client:
        response = await client.get(f"/api/episodes/{asset.episode_id}/playable-media")

    assert response.status_code == 200
    assert response.json()["path"] == "/data/media/playable/asset.mp4"
    assert response.json()["current"] is True


@pytest.mark.anyio
async def test_get_latest_episode_transcoding_job() -> None:
    asset = make_asset()
    job = MediaTranscodingJob(
        id=uuid7(),
        media_asset_id=asset.id,
        variant_id=uuid7(),
        status=MediaTranscodingJobStatus.PROCESSING.value,
        operation="transcode",
        source_path=asset.path,
        source_metadata_updated_at=asset.metadata_updated_at,
        attempt_count=1,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )

    anime_service = MagicMock(spec=AnimeService)
    anime_service.get_episode = AsyncMock()
    asset_service = MagicMock(spec=MediaAssetService)
    asset_service.get_for_episode = AsyncMock(return_value=asset)
    variant_service = MagicMock()
    job_service = MagicMock(spec=MediaTranscodingJobService)
    job_service.get_latest_job = AsyncMock(return_value=job)

    async with make_client(anime_service, asset_service, variant_service, job_service) as client:
        response = await client.get(
            f"/api/episodes/{asset.episode_id}/playable-media-transcoding-jobs/latest",
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(job.id)
    assert response.json()["status"] == "processing"