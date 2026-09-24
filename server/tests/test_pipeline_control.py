from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import pytest
from animedownloader_api.pipeline_control import EpisodePipelineControlService
from animedownloader_api.schemas import (
    EpisodePipelineCurrentStage,
    EpisodePipelineStageStatus,
)
from animedownloader_download import DownloadJobStatus
from animedownloader_media_processing import (
    MediaProcessingJobStatus,
)


def build_service() -> tuple[EpisodePipelineControlService, dict[str, MagicMock]]:
    service = EpisodePipelineControlService(
        MagicMock(),
        download_dispatcher=MagicMock(),
        media_dispatcher=MagicMock(),
    )
    mocks = {
        "anime": MagicMock(),
        "downloads": MagicMock(),
        "processing": MagicMock(),
        "assets": MagicMock(),
        "preparation": MagicMock(),
        "variants": MagicMock(),
        "streaming": MagicMock(),
        "download_dispatcher": MagicMock(),
        "media_dispatcher": MagicMock(),
    }
    for name, mock in mocks.items():
        setattr(service, "_" + name, mock)
    return service, mocks


@pytest.mark.anyio
async def test_retry_continues_to_streaming_without_creating_download_job() -> None:
    service, mocks = build_service()
    episode_id = uuid7()
    download_id = uuid7()
    package_job_id = uuid7()

    download = SimpleNamespace(
        id=download_id,
        job_status=DownloadJobStatus.COMPLETED,
    )
    processing = SimpleNamespace(
        id=uuid7(),
        job_status=MediaProcessingJobStatus.COMPLETED,
    )
    asset = SimpleNamespace(
        id=uuid7(),
        path="media/source.mkv",
        metadata_updated_at=SimpleNamespace(),
        metadata_ready=True,
        thumbnail_ready=True,
    )
    variant = SimpleNamespace(
        id=uuid7(),
        path="playable/video.mp4",
        updated_at=SimpleNamespace(),
    )
    variant.is_current = MagicMock(return_value=True)
    package_job = SimpleNamespace(id=package_job_id)

    mocks["anime"].get_episode = AsyncMock()
    mocks["downloads"].get_latest_job = AsyncMock(return_value=download)
    mocks["downloads"].create_job = AsyncMock()
    mocks["processing"].get_latest_job = AsyncMock(return_value=processing)
    mocks["assets"].get_for_episode = AsyncMock(return_value=asset)
    mocks["variants"].get_playable_variant = AsyncMock(return_value=variant)
    mocks["streaming"].get_active_job = AsyncMock(return_value=None)
    mocks["streaming"].get_for_variant = AsyncMock(return_value=None)
    mocks["streaming"].create_job = AsyncMock(return_value=package_job)
    mocks["download_dispatcher"].enqueue = AsyncMock()
    mocks["media_dispatcher"].enqueue_packaging = AsyncMock()

    result = await service.retry(episode_id)

    assert result.stage is EpisodePipelineCurrentStage.STREAMING
    assert result.status is EpisodePipelineStageStatus.PENDING
    assert result.job_id == package_job_id
    mocks["downloads"].create_job.assert_not_awaited()
    mocks["download_dispatcher"].enqueue.assert_not_awaited()
    mocks["media_dispatcher"].enqueue_packaging.assert_awaited_once_with(package_job_id)


@pytest.mark.anyio
async def test_retry_failed_processing_without_creating_download_job() -> None:
    service = build_service()
    episode_id = uuid7()
    download_id = uuid7()
    processing_id = uuid7()

    download = SimpleNamespace(
        id=download_id,
        job_status=DownloadJobStatus.COMPLETED,
    )
    processing = SimpleNamespace(
        id=processing_id,
        job_status=MediaProcessingJobStatus.FAILED,
    )
    retried = SimpleNamespace(
        id=processing_id,
        job_status=MediaProcessingJobStatus.PENDING,
    )

    mocks["anime"].get_episode = AsyncMock()
    mocks["downloads"].get_latest_job = AsyncMock(return_value=download)
    mocks["downloads"].create_job = AsyncMock()
    mocks["processing"].get_latest_job = AsyncMock(return_value=processing)
    mocks["processing"].retry_job = AsyncMock(return_value=retried)
    mocks["media_dispatcher"].enqueue = AsyncMock()

    result = await service.retry(episode_id)

    assert result.stage is EpisodePipelineCurrentStage.PROCESSING
    assert result.status is EpisodePipelineStageStatus.PENDING
    assert result.job_id == processing_id
    service._downloads.create_job.assert_not_awaited()
    mocks["media_dispatcher"].enqueue.assert_awaited_once_with(processing_id)
