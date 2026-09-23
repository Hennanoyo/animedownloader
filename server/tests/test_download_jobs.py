from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import get_download_job_service
from animedownloader_download import (
    DownloadJob,
    DownloadJobNotFoundError,
    DownloadJobService,
    DownloadJobStatus,
    InvalidDownloadJobTransitionError,
)


def make_job(status: DownloadJobStatus = DownloadJobStatus.PENDING) -> DownloadJob:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    return DownloadJob(
        id=uuid7(),
        episode_id=uuid7(),
        status=status.value,
        downloaded_bytes=0,
        total_bytes=100,
        attempt_count=0,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )


def make_client(service: MagicMock) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_download_job_service] = lambda: service
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.anyio
async def test_get_download_job() -> None:
    service = MagicMock(spec=DownloadJobService)
    service.get_job = AsyncMock(return_value=make_job())

    async with make_client(service) as client:
        response = await client.get("/api/download-jobs/" + str(uuid7()))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["downloaded_bytes"] == 0
    service.get_job.assert_awaited_once()


@pytest.mark.anyio
async def test_missing_download_job_is_404() -> None:
    service = MagicMock(spec=DownloadJobService)
    service.get_job = AsyncMock(side_effect=DownloadJobNotFoundError(uuid7()))

    async with make_client(service) as client:
        response = await client.get("/api/download-jobs/" + str(uuid7()))

    assert response.status_code == 404


def test_download_job_state_transitions() -> None:
    job = make_job()

    job.transition_to(DownloadJobStatus.DOWNLOADING)
    assert job.job_status is DownloadJobStatus.DOWNLOADING
    assert job.attempt_count == 1
    assert job.started_at is not None

    job.transition_to(
        DownloadJobStatus.COMPLETED,
        downloaded_bytes=100,
        total_bytes=100,
    )
    assert job.job_status is DownloadJobStatus.COMPLETED
    assert job.downloaded_bytes == 100
    assert job.total_bytes == 100
    assert job.completed_at is not None
    assert job.error_message is None


def test_invalid_download_job_transition() -> None:
    job = make_job(DownloadJobStatus.COMPLETED)

    with pytest.raises(InvalidDownloadJobTransitionError):
        job.transition_to(DownloadJobStatus.DOWNLOADING)


def test_pause_resume_keeps_attempt_count() -> None:
    job = make_job()

    job.transition_to(DownloadJobStatus.DOWNLOADING)
    job.transition_to(DownloadJobStatus.PAUSED)
    job.transition_to(DownloadJobStatus.DOWNLOADING)

    assert job.job_status is DownloadJobStatus.DOWNLOADING
    assert job.attempt_count == 1
