from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from animedownloader_media_asset import MediaAsset, MediaAssetMetadata, MediaAssetService


def make_service() -> MediaAssetService:
    return MediaAssetService(MagicMock())


def make_metadata() -> MediaAssetMetadata:
    return MediaAssetMetadata(
        format_name="matroska,webm",
        duration_seconds=60.0,
        size_bytes=1024,
        video_codec="hevc",
        audio_codec="aac",
        width=1920,
        height=1080,
        frame_rate="24000/1001",
    )


@pytest.mark.anyio
async def test_upsert_creates_media_asset() -> None:
    service = make_service()
    service.assets.get_for_episode = AsyncMock(return_value=None)

    async def add(asset: MediaAsset) -> None:
        assert asset.processing_job_id is not None
        assert asset.path is not None
        assert asset.metadata_ready

    service.assets.add = AsyncMock(side_effect=add)

    episode_id = uuid7()
    processing_job_id = uuid7()
    path = "/downloads/example/episode.mkv"
    metadata = make_metadata()

    asset = await service.upsert(
        episode_id=episode_id,
        processing_job_id=processing_job_id,
        media_path=path,
        metadata=metadata,
    )

    assert asset.episode_id == episode_id
    assert asset.processing_job_id == processing_job_id
    assert asset.path == path
    assert asset.format_name == metadata.format_name
    assert asset.duration_seconds == metadata.duration_seconds
    assert asset.size_bytes == metadata.size_bytes
    assert asset.video_codec == metadata.video_codec
    assert asset.audio_codec == metadata.audio_codec
    assert asset.width == metadata.width
    assert asset.height == metadata.height
    assert asset.frame_rate == metadata.frame_rate
    assert asset.metadata_updated_at is not None
    assert asset.metadata_ready
    service.assets.add.assert_awaited_once_with(asset)


@pytest.mark.anyio
async def test_upsert_updates_existing_episode_asset() -> None:
    service = make_service()
    existing = MagicMock()
    service.assets.get_for_episode = AsyncMock(return_value=existing)
    service.assets.add = AsyncMock()
    metadata = make_metadata()

    episode_id = uuid7()
    processing_job_id = uuid7()
    path = "/downloads/example/episode.mkv"

    result = await service.upsert(
        episode_id=episode_id,
        processing_job_id=processing_job_id,
        media_path=path,
        metadata=metadata,
    )

    assert result is existing
    assert existing.processing_job_id == processing_job_id
    assert existing.path == path
    existing.update_metadata.assert_called_once_with(metadata)
    service.assets.add.assert_not_awaited()
