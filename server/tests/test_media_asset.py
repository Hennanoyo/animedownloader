from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from animedownloader_media_asset import MediaAssetService


def make_service() -> MediaAssetService:
    return MediaAssetService(MagicMock())


@pytest.mark.anyio
async def test_upsert_creates_media_asset() -> None:
    service = make_service()
    service.assets.get_for_episode = AsyncMock(return_value=None)
    service.assets.add = AsyncMock()

    episode_id = uuid7()
    processing_job_id = uuid7()
    path = "/downloads/example/episode.mkv"

    asset = await service.upsert(
        episode_id=episode_id,
        processing_job_id=processing_job_id,
        media_path=path,
    )

    assert asset.episode_id == episode_id
    assert asset.processing_job_id == processing_job_id
    assert asset.path == path
    service.assets.add.assert_awaited_once_with(asset)


@pytest.mark.anyio
async def test_upsert_updates_existing_episode_asset() -> None:
    service = make_service()
    existing = MagicMock()
    service.assets.get_for_episode = AsyncMock(return_value=existing)
    service.assets.add = AsyncMock()

    episode_id = uuid7()
    processing_job_id = uuid7()
    path = "/downloads/example/episode.mkv"

    result = await service.upsert(
        episode_id=episode_id,
        processing_job_id=processing_job_id,
        media_path=path,
    )

    assert result is existing
    assert existing.processing_job_id == processing_job_id
    assert existing.path == path
    service.assets.add.assert_not_awaited()
