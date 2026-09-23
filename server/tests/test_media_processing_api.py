from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_media_processing_job_service,
    get_media_processing_task_dispatcher,
)
from animedownloader_api.media_processing_queue import MediaProcessingTaskDispatcher
from animedownloader_api.schemas import MediaProcessingJobResponse
from animedownloader_media_processing import (
    MediaProcessingJob,
    MediaProcessingJobNotFoundError,
    MediaProcessingJobService,
    MediaProcessingJobStatus,
)


def make_job(status: MediaProcessingJobStatus) -> MediaProcessingJob:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    return MediaProcessingJob(
        id=uuid7(),
        episode_id=uuid7(),
        download_job_id=uuid7(),
        status=status.value,
        media_path=None,
        probe_metadata=None,
        attempt_count=1 if status is not MediaProcessingJobStatus.PENDING else 0,
        error_message=None,
        started_at=now if status is not MediaProcessingJobStatus.PENDING else None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )


def make_client(
    service: MagicMock,
    dispatcher: MagicMock,
) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_media_processing_job_service] = lambda: service
    app.dependency_overrides[get_media_processing_task_dispatcher] = lambda: dispatcher
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.mark.anyio
async def test_get_media_processing_job() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    job = make_job(MediaProcessingJobStatus.PROCESSING)
    service.get_job = AsyncMock(return_value=job)

    async with make_client(service, dispatcher) as client:
        response = await client.get(f"/api/media-processing-jobs/{job.id}")

    assert response.status_code == 200
    payload = MediaProcessingJobResponse.model_validate(response.json())
    assert payload.id == job.id
    assert payload.status is MediaProcessingJobStatus.PROCESSING
    service.get_job.assert_awaited_once_with(job.id)


@pytest.mark.anyio
async def test_missing_media_processing_job_is_404() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    job_id = uuid7()
    service.get_job = AsyncMock(side_effect=MediaProcessingJobNotFoundError(job_id))

    async with make_client(service, dispatcher) as client:
        response = await client.get(f"/api/media-processing-jobs/{job_id}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_retry_media_processing_job_enqueues_task() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    job = make_job(MediaProcessingJobStatus.PENDING)
    service.retry_job = AsyncMock(return_value=job)
    dispatcher.enqueue = AsyncMock()

    async with make_client(service, dispatcher) as client:
        response = await client.post(f"/api/media-processing-jobs/{job.id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    service.retry_job.assert_awaited_once_with(job.id)
    dispatcher.enqueue.assert_awaited_once_with(job.id)


@pytest.mark.anyio
async def test_retry_returns_503_when_task_queue_fails() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    job = make_job(MediaProcessingJobStatus.PENDING)
    service.retry_job = AsyncMock(return_value=job)
    dispatcher.enqueue = AsyncMock(side_effect=RuntimeError("redis unavailable"))
    service.mark_failed = AsyncMock(return_value=job)

    async with make_client(service, dispatcher) as client:
        response = await client.post(f"/api/media-processing-jobs/{job.id}/retry")

    assert response.status_code == 503
    service.mark_failed.assert_awaited_once_with(
        job.id,
        error_message="Failed to enqueue media processing task.",
    )


@pytest.mark.anyio
async def test_get_latest_episode_media_processing_job() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    job = make_job(MediaProcessingJobStatus.COMPLETED)
    service.get_latest_job = AsyncMock(return_value=job)

    async with make_client(service, dispatcher) as client:
        response = await client.get(
            f"/api/episodes/{job.episode_id}/media-processing-jobs/latest",
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(job.id)
    assert response.json()["status"] == "completed"
    service.get_latest_job.assert_awaited_once_with(job.episode_id)
