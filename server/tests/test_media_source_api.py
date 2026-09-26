from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import get_media_source_service
from animedownloader_api.media_source import (
    EpisodeMediaSource,
    MediaSourceCandidate,
    MediaSourceOrphan,
    MediaSourceRecoveryConflictError,
    MediaSourceService,
)
from animedownloader_download import DownloadJobStatus
from animedownloader_media_processing import MediaProcessingJobStatus


def make_client(service: MagicMock) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_media_source_service] = lambda: service
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.mark.anyio
async def test_get_episode_media_source_returns_candidates() -> None:
    service = MagicMock(spec=MediaSourceService)
    episode_id = uuid7()
    job_id = uuid7()
    processing_id = uuid7()
    service.get_episode_source = AsyncMock(
        return_value=EpisodeMediaSource(
            episode_id=episode_id,
            download_job_id=job_id,
            download_status=DownloadJobStatus.COMPLETED,
            status="ambiguous",
            root="/downloads/" + str(job_id),
            selected_path=None,
            candidates=(
                MediaSourceCandidate("episode-01.mkv"),
                MediaSourceCandidate("episode-01.mp4"),
            ),
            processing_job_id=processing_id,
            processing_status=MediaProcessingJobStatus.PENDING,
        )
    )

    async with make_client(service) as client:
        response = await client.get(f"/api/episodes/{episode_id}/media-source")

    assert response.status_code == 200
    assert response.json()["status"] == "ambiguous"
    assert response.json()["candidates"] == [
        {"path": "episode-01.mkv"},
        {"path": "episode-01.mp4"},
    ]
    service.get_episode_source.assert_awaited_once_with(episode_id)


@pytest.mark.anyio
async def test_select_episode_media_source_enqueues_processing() -> None:
    service = MagicMock(spec=MediaSourceService)
    episode_id = uuid7()
    job_id = uuid7()
    service.select_source = AsyncMock(
        return_value=SimpleNamespace(id=job_id),
    )

    async with make_client(service) as client:
        response = await client.post(
            f"/api/episodes/{episode_id}/media-source/select",
            json={"path": "release/episode.mkv"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "stage": "processing",
        "job_id": str(job_id),
        "status": "pending",
    }
    service.select_source.assert_awaited_once_with(
        episode_id,
        "release/episode.mkv",
    )


@pytest.mark.anyio
async def test_reprocess_episode_media_source_returns_409_on_conflict() -> None:
    service = MagicMock(spec=MediaSourceService)
    episode_id = uuid7()
    service.reprocess = AsyncMock(
        side_effect=MediaSourceRecoveryConflictError(
            "Media processing is already in progress.",
        ),
    )

    async with make_client(service) as client:
        response = await client.post(
            f"/api/episodes/{episode_id}/media-source/reprocess",
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Media processing is already in progress."


@pytest.mark.anyio
async def test_redownload_episode_media_source_returns_new_download_job() -> None:
    service = MagicMock(spec=MediaSourceService)
    episode_id = uuid7()
    job_id = uuid7()
    service.redownload = AsyncMock(
        return_value=SimpleNamespace(id=job_id),
    )

    async with make_client(service) as client:
        response = await client.post(
            f"/api/episodes/{episode_id}/media-source/redownload",
        )

    assert response.status_code == 200
    assert response.json() == {
        "stage": "download",
        "job_id": str(job_id),
        "status": "pending",
    }
    service.redownload.assert_awaited_once_with(episode_id)


@pytest.mark.anyio
async def test_list_media_source_orphans() -> None:
    service = MagicMock(spec=MediaSourceService)
    orphan = MediaSourceOrphan(
        directory_id=uuid7(),
        path="/downloads/orphan",
    )
    service.list_orphans = AsyncMock(return_value=[orphan])

    async with make_client(service) as client:
        response = await client.get("/api/media-sources/orphans")

    assert response.status_code == 200
    assert response.json() == [
        {
            "directory_id": str(orphan.directory_id),
            "path": orphan.path,
        }
    ]


@pytest.mark.anyio
async def test_delete_media_source_orphan() -> None:
    service = MagicMock(spec=MediaSourceService)
    directory_id = uuid7()
    service.delete_orphan = AsyncMock()

    async with make_client(service) as client:
        response = await client.delete(
            f"/api/media-sources/orphans/{directory_id}",
        )

    assert response.status_code == 204
    service.delete_orphan.assert_awaited_once_with(directory_id)
