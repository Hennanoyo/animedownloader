from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_download_job_service,
    get_qbittorrent_client,
)
from animedownloader_download import DownloadJob, DownloadJobService, DownloadJobStatus
from animedownloader_qbittorrent import QBittorrentClient
from animedownloader_torrent import TorrentInfo, TorrentStatus


def make_job(status: DownloadJobStatus) -> DownloadJob:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    return DownloadJob(
        id=uuid7(),
        episode_id=uuid7(),
        status=status.value,
        downloaded_bytes=500,
        total_bytes=1000,
        attempt_count=1,
        error_message=None,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )


def make_torrent() -> TorrentInfo:
    return TorrentInfo(
        id="torrent-1",
        name="Episode One",
        status=TorrentStatus.DOWNLOADING,
        progress=0.5,
        downloaded_bytes=500,
        total_bytes=1000,
        save_path="/downloads/job",
        tags=frozenset({"animedownloader:job-test"}),
    )


def make_client(
    service: MagicMock,
    torrent_client: MagicMock,
) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_download_job_service] = lambda: service
    app.dependency_overrides[get_qbittorrent_client] = lambda: torrent_client
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.mark.anyio
async def test_pause_download_job() -> None:
    job = make_job(DownloadJobStatus.DOWNLOADING)
    service = MagicMock(spec=DownloadJobService)
    service.mark_paused = AsyncMock(return_value=job)
    torrent_client = MagicMock(spec=QBittorrentClient)
    torrent_client.find_by_tag = AsyncMock(return_value=make_torrent())
    torrent_client.pause = AsyncMock()

    async with make_client(service, torrent_client) as client:
        response = await client.post("/api/download-jobs/" + str(job.id) + "/pause")

    assert response.status_code == 200
    torrent_client.pause.assert_awaited_once_with("torrent-1")


@pytest.mark.anyio
async def test_resume_download_job() -> None:
    job = make_job(DownloadJobStatus.PAUSED)
    service = MagicMock(spec=DownloadJobService)
    service.mark_downloading = AsyncMock(return_value=job)
    torrent = make_torrent()
    torrent = TorrentInfo(
        id=torrent.id,
        name=torrent.name,
        status=TorrentStatus.PAUSED,
        progress=torrent.progress,
        downloaded_bytes=torrent.downloaded_bytes,
        total_bytes=torrent.total_bytes,
        save_path=torrent.save_path,
        tags=torrent.tags,
    )
    torrent_client = MagicMock(spec=QBittorrentClient)
    torrent_client.find_by_tag = AsyncMock(return_value=torrent)
    torrent_client.resume = AsyncMock()

    async with make_client(service, torrent_client) as client:
        response = await client.post("/api/download-jobs/" + str(job.id) + "/resume")

    assert response.status_code == 200
    torrent_client.resume.assert_awaited_once_with("torrent-1")


@pytest.mark.anyio
async def test_cancel_download_job_removes_torrent() -> None:
    job = make_job(DownloadJobStatus.DOWNLOADING)
    service = MagicMock(spec=DownloadJobService)
    service.mark_cancelled = AsyncMock(return_value=job)
    torrent_client = MagicMock(spec=QBittorrentClient)
    torrent_client.find_by_tag = AsyncMock(return_value=make_torrent())
    torrent_client.remove = AsyncMock()

    async with make_client(service, torrent_client) as client:
        response = await client.post("/api/download-jobs/" + str(job.id) + "/cancel")

    assert response.status_code == 200
    torrent_client.remove.assert_awaited_once_with("torrent-1", delete_files=True)


@pytest.mark.anyio
async def test_delete_completed_download_job() -> None:
    job = make_job(DownloadJobStatus.COMPLETED)
    service = MagicMock(spec=DownloadJobService)
    service.get_job = AsyncMock(return_value=job)
    service.delete_job = AsyncMock()
    torrent_client = MagicMock(spec=QBittorrentClient)
    torrent_client.find_by_tag = AsyncMock(return_value=None)

    async with make_client(service, torrent_client) as client:
        response = await client.delete("/api/download-jobs/" + str(job.id))

    assert response.status_code == 204
    service.delete_job.assert_awaited_once_with(job.id)
