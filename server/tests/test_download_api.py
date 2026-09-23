from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_download_job_service,
    get_download_task_dispatcher,
)
from animedownloader_api.task_queue import DownloadTaskDispatcher
from animedownloader_download import (
    ActiveDownloadJobError,
    DownloadJob,
    DownloadJobService,
    DownloadJobStatus,
)


def make_job(status: DownloadJobStatus = DownloadJobStatus.PENDING) -> DownloadJob:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    return DownloadJob(
        id=uuid7(),
        episode_id=uuid7(),
        status=status.value,
        downloaded_bytes=0,
        total_bytes=1000,
        attempt_count=0,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )


def make_client(
    service: MagicMock,
    dispatcher: MagicMock,
) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_download_job_service] = lambda: service
    app.dependency_overrides[get_download_task_dispatcher] = lambda: dispatcher
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.mark.anyio
async def test_create_download_job_enqueues_task() -> None:
    service = MagicMock(spec=DownloadJobService)
    dispatcher = MagicMock(spec=DownloadTaskDispatcher)
    job = make_job()
    service.create_job = AsyncMock(return_value=job)
    dispatcher.enqueue = AsyncMock()

    async with make_client(service, dispatcher) as client:
        response = await client.post(f"/api/episodes/{job.episode_id}/download-jobs")

    assert response.status_code == 201
    assert response.json()["id"] == str(job.id)
    service.create_job.assert_awaited_once_with(job.episode_id)
    dispatcher.enqueue.assert_awaited_once_with(job.id)


@pytest.mark.anyio
async def test_duplicate_download_job_returns_409() -> None:
    service = MagicMock(spec=DownloadJobService)
    dispatcher = MagicMock(spec=DownloadTaskDispatcher)
    episode_id = uuid7()
    active_job_id = uuid7()
    service.create_job = AsyncMock(side_effect=ActiveDownloadJobError(episode_id, active_job_id))

    async with make_client(service, dispatcher) as client:
        response = await client.post(f"/api/episodes/{episode_id}/download-jobs")

    assert response.status_code == 409
    assert str(active_job_id) in response.json()["detail"]
    dispatcher.enqueue.assert_not_called()


@pytest.mark.anyio
async def test_create_download_job_marks_failed_when_enqueue_fails() -> None:
    service = MagicMock(spec=DownloadJobService)
    dispatcher = MagicMock(spec=DownloadTaskDispatcher)
    job = make_job()
    service.create_job = AsyncMock(return_value=job)
    dispatcher.enqueue = AsyncMock(side_effect=RuntimeError("redis unavailable"))
    service.mark_failed = AsyncMock(return_value=job)

    async with make_client(service, dispatcher) as client:
        response = await client.post("/api/episodes/" + str(job.episode_id) + "/download-jobs")

    assert response.status_code == 503
    service.mark_failed.assert_awaited_once_with(
        job.id,
        error_message="Failed to enqueue download task.",
    )


@pytest.mark.anyio
async def test_get_latest_episode_download_job() -> None:
    service = MagicMock(spec=DownloadJobService)
    dispatcher = MagicMock(spec=DownloadTaskDispatcher)
    job = make_job(DownloadJobStatus.COMPLETED)
    service.get_latest_job = AsyncMock(return_value=job)

    async with make_client(service, dispatcher) as client:
        response = await client.get(f"/api/episodes/{job.episode_id}/download-jobs/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(job.id)
    assert payload["status"] == "completed"
    service.get_latest_job.assert_awaited_once_with(job.episode_id)


@pytest.mark.anyio
async def test_latest_episode_download_job_returns_null_when_missing() -> None:
    service = MagicMock(spec=DownloadJobService)
    dispatcher = MagicMock(spec=DownloadTaskDispatcher)
    episode_id = uuid7()
    service.get_latest_job = AsyncMock(return_value=None)

    async with make_client(service, dispatcher) as client:
        response = await client.get(f"/api/episodes/{episode_id}/download-jobs/latest")

    assert response.status_code == 200
    assert response.json() is None
    service.get_latest_job.assert_awaited_once_with(episode_id)
