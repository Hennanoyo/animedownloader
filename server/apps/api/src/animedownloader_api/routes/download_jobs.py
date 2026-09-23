from typing import Annotated
from uuid import UUID

from animedownloader_download import DownloadJob, DownloadJobService
from animedownloader_qbittorrent import QBittorrentClient
from fastapi import APIRouter, Depends

from animedownloader_api.dependencies import (
    get_download_job_service,
    get_qbittorrent_client,
)
from animedownloader_api.download_control import DownloadControlService
from animedownloader_api.schemas import DownloadJobResponse

router = APIRouter(prefix="/api/download-jobs", tags=["download-jobs"])
QBittorrentClientDependency = Annotated[
    QBittorrentClient,
    Depends(get_qbittorrent_client),
]
DownloadJobServiceDependency = Annotated[
    DownloadJobService,
    Depends(get_download_job_service),
]


@router.get("/{job_id}", response_model=DownloadJobResponse)
async def get_download_job(
    job_id: UUID,
    service: DownloadJobServiceDependency,
) -> DownloadJob:
    return await service.get_job(job_id)


@router.post("/{job_id}/pause", response_model=DownloadJobResponse)
async def pause_download_job(
    job_id: UUID,
    service: DownloadJobServiceDependency,
    torrent_client: QBittorrentClientDependency,
) -> DownloadJob:
    return await DownloadControlService(service, torrent_client).pause(job_id)


@router.post("/{job_id}/resume", response_model=DownloadJobResponse)
async def resume_download_job(
    job_id: UUID,
    service: DownloadJobServiceDependency,
    torrent_client: QBittorrentClientDependency,
) -> DownloadJob:
    return await DownloadControlService(service, torrent_client).resume(job_id)


@router.post("/{job_id}/cancel", response_model=DownloadJobResponse)
async def cancel_download_job(
    job_id: UUID,
    service: DownloadJobServiceDependency,
    torrent_client: QBittorrentClientDependency,
) -> DownloadJob:
    return await DownloadControlService(service, torrent_client).cancel(job_id)


@router.delete("/{job_id}", status_code=204)
async def delete_download_job(
    job_id: UUID,
    service: DownloadJobServiceDependency,
    torrent_client: QBittorrentClientDependency,
) -> None:
    await DownloadControlService(service, torrent_client).delete(job_id)
