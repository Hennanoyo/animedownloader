from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_download_job_service,
    get_media_asset_service,
    get_media_processing_job_service,
    get_media_processing_task_dispatcher,
)
from animedownloader_api.media_processing_queue import MediaProcessingTaskDispatcher
from animedownloader_api.schemas import MediaProcessingJobResponse
from animedownloader_download import (
    DownloadJob,
    DownloadJobService,
    DownloadJobStatus,
)
from animedownloader_media_asset import MediaAssetService
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
        download_directory="download-dir",
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
    download_service: MagicMock | None = None,
    media_asset_service: MagicMock | None = None,
) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_media_processing_job_service] = lambda: service
    app.dependency_overrides[get_media_processing_task_dispatcher] = lambda: dispatcher
    if download_service is not None:
        app.dependency_overrides[get_download_job_service] = lambda: download_service
    if media_asset_service is not None:
        app.dependency_overrides[get_media_asset_service] = lambda: media_asset_service
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


@pytest.mark.anyio
async def test_create_media_processing_job_from_completed_download() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    download_service = MagicMock(spec=DownloadJobService)
    job = make_job(MediaProcessingJobStatus.PENDING)
    download_job = DownloadJob(
        id=uuid7(),
        episode_id=job.episode_id,
        status=DownloadJobStatus.COMPLETED.value,
        downloaded_bytes=100,
        total_bytes=100,
        attempt_count=1,
        error_message=None,
        started_at=datetime(2026, 9, 23, tzinfo=UTC),
        completed_at=datetime(2026, 9, 23, tzinfo=UTC),
        created_at=datetime(2026, 9, 23, tzinfo=UTC),
        updated_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    download_service.get_job = AsyncMock(return_value=download_job)
    service.create_for_download_job = AsyncMock(return_value=job)
    dispatcher.enqueue = AsyncMock()
    media_asset_service = MagicMock(spec=MediaAssetService)
    media_asset_service.get_for_episode = AsyncMock(return_value=None)

    async with make_client(
        service,
        dispatcher,
        download_service,
        media_asset_service,
    ) as client:
        response = await client.post(
            f"/api/media-processing-jobs/from-download-job/{download_job.id}",
        )

    assert response.status_code == 201
    assert response.json()["id"] == str(job.id)
    service.create_for_download_job.assert_awaited_once_with(download_job.id)
    dispatcher.enqueue.assert_awaited_once_with(job.id)


@pytest.mark.anyio
async def test_manual_media_processing_requeues_completed_job_when_asset_is_missing() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    download_service = MagicMock(spec=DownloadJobService)
    media_asset_service = MagicMock(spec=MediaAssetService)
    job = make_job(MediaProcessingJobStatus.COMPLETED)
    download_job = DownloadJob(
        id=uuid7(),
        episode_id=job.episode_id,
        status=DownloadJobStatus.COMPLETED.value,
        downloaded_bytes=100,
        total_bytes=100,
        attempt_count=1,
        error_message=None,
        started_at=datetime(2026, 9, 23, tzinfo=UTC),
        completed_at=datetime(2026, 9, 23, tzinfo=UTC),
        created_at=datetime(2026, 9, 23, tzinfo=UTC),
        updated_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    download_service.get_job = AsyncMock(return_value=download_job)
    service.create_for_download_job = AsyncMock(return_value=job)
    media_asset_service.get_for_episode = AsyncMock(return_value=None)
    dispatcher.enqueue = AsyncMock()

    async with make_client(
        service,
        dispatcher,
        download_service,
        media_asset_service,
    ) as client:
        response = await client.post(
            f"/api/media-processing-jobs/from-download-job/{download_job.id}",
        )

    assert response.status_code == 201
    media_asset_service.get_for_episode.assert_awaited_once_with(job.episode_id)
    dispatcher.enqueue.assert_awaited_once_with(job.id)


@pytest.mark.anyio
async def test_manual_media_processing_requeues_completed_job_when_asset_metadata_is_missing() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    download_service = MagicMock(spec=DownloadJobService)
    media_asset_service = MagicMock(spec=MediaAssetService)
    job = make_job(MediaProcessingJobStatus.COMPLETED)
    download_job = DownloadJob(
        id=uuid7(),
        episode_id=job.episode_id,
        status=DownloadJobStatus.COMPLETED.value,
        downloaded_bytes=100,
        total_bytes=100,
        attempt_count=1,
        error_message=None,
        started_at=datetime(2026, 9, 23, tzinfo=UTC),
        completed_at=datetime(2026, 9, 23, tzinfo=UTC),
        created_at=datetime(2026, 9, 23, tzinfo=UTC),
        updated_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    stale_asset = MagicMock()
    stale_asset.metadata_ready = False
    stale_asset.subtitle_tracks_ready = True
    stale_asset.subtitle_processing_ready = False
    download_service.get_job = AsyncMock(return_value=download_job)
    service.create_for_download_job = AsyncMock(return_value=job)
    media_asset_service.get_for_episode = AsyncMock(return_value=stale_asset)
    dispatcher.enqueue = AsyncMock()

    async with make_client(
        service,
        dispatcher,
        download_service,
        media_asset_service,
    ) as client:
        response = await client.post(
            f"/api/media-processing-jobs/from-download-job/{download_job.id}",
        )

    assert response.status_code == 201
    media_asset_service.get_for_episode.assert_awaited_once_with(job.episode_id)
    dispatcher.enqueue.assert_awaited_once_with(job.id)


@pytest.mark.anyio
async def test_manual_media_processing_does_not_requeue_completed_job_with_asset() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    download_service = MagicMock(spec=DownloadJobService)
    media_asset_service = MagicMock(spec=MediaAssetService)
    job = make_job(MediaProcessingJobStatus.COMPLETED)
    download_job = DownloadJob(
        id=uuid7(),
        episode_id=job.episode_id,
        status=DownloadJobStatus.COMPLETED.value,
        downloaded_bytes=100,
        total_bytes=100,
        attempt_count=1,
        error_message=None,
        started_at=datetime(2026, 9, 23, tzinfo=UTC),
        completed_at=datetime(2026, 9, 23, tzinfo=UTC),
        created_at=datetime(2026, 9, 23, tzinfo=UTC),
        updated_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    download_service.get_job = AsyncMock(return_value=download_job)
    service.create_for_download_job = AsyncMock(return_value=job)
    media_asset_service.get_for_episode = AsyncMock(return_value=MagicMock())

    async with make_client(
        service,
        dispatcher,
        download_service,
        media_asset_service,
    ) as client:
        response = await client.post(
            f"/api/media-processing-jobs/from-download-job/{download_job.id}",
        )

    assert response.status_code == 201
    dispatcher.enqueue.assert_not_awaited()


@pytest.mark.anyio
async def test_manual_media_processing_does_not_requeue_processing_job() -> None:
    service = MagicMock(spec=MediaProcessingJobService)
    dispatcher = MagicMock(spec=MediaProcessingTaskDispatcher)
    download_service = MagicMock(spec=DownloadJobService)
    job = make_job(MediaProcessingJobStatus.PROCESSING)
    download_job = DownloadJob(
        id=uuid7(),
        episode_id=job.episode_id,
        status=DownloadJobStatus.COMPLETED.value,
        downloaded_bytes=100,
        total_bytes=100,
        attempt_count=1,
        error_message=None,
        started_at=datetime(2026, 9, 23, tzinfo=UTC),
        completed_at=datetime(2026, 9, 23, tzinfo=UTC),
        created_at=datetime(2026, 9, 23, tzinfo=UTC),
        updated_at=datetime(2026, 9, 23, tzinfo=UTC),
    )
    download_service.get_job = AsyncMock(return_value=download_job)
    service.create_for_download_job = AsyncMock(return_value=job)

    async with make_client(service, dispatcher, download_service) as client:
        response = await client.post(
            f"/api/media-processing-jobs/from-download-job/{download_job.id}",
        )

    assert response.status_code == 201
    dispatcher.enqueue.assert_not_awaited()
