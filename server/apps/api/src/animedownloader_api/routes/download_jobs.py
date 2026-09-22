from typing import Annotated
from uuid import UUID

from animedownloader_download import DownloadJob, DownloadJobService
from fastapi import APIRouter, Depends

from animedownloader_api.dependencies import get_download_job_service
from animedownloader_api.schemas import DownloadJobResponse

router = APIRouter(prefix="/api/download-jobs", tags=["download-jobs"])
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
