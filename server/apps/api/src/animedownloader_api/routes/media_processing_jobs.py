from typing import Annotated
from uuid import UUID

from animedownloader_media_processing import MediaProcessingJob, MediaProcessingJobService
from fastapi import APIRouter, Depends, HTTPException, status

from animedownloader_api.dependencies import (
    get_media_processing_job_service,
    get_media_processing_task_dispatcher,
)
from animedownloader_api.media_processing_queue import MediaProcessingTaskDispatcher
from animedownloader_api.schemas import MediaProcessingJobResponse

router = APIRouter(
    prefix="/api/media-processing-jobs",
    tags=["media-processing-jobs"],
)

MediaProcessingJobServiceDependency = Annotated[
    MediaProcessingJobService,
    Depends(get_media_processing_job_service),
]
MediaProcessingTaskDispatcherDependency = Annotated[
    MediaProcessingTaskDispatcher,
    Depends(get_media_processing_task_dispatcher),
]


@router.get("/{job_id}", response_model=MediaProcessingJobResponse)
async def get_media_processing_job(
    job_id: UUID,
    service: MediaProcessingJobServiceDependency,
) -> MediaProcessingJob:
    return await service.get_job(job_id)


@router.post(
    "/{job_id}/retry",
    response_model=MediaProcessingJobResponse,
)
async def retry_media_processing_job(
    job_id: UUID,
    service: MediaProcessingJobServiceDependency,
    dispatcher: MediaProcessingTaskDispatcherDependency,
) -> MediaProcessingJob:
    job = await service.retry_job(job_id)
    try:
        await dispatcher.enqueue(job.id)
    except Exception as exc:
        await service.mark_failed(
            job.id,
            error_message="Failed to enqueue media processing task.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media processing task queue is temporarily unavailable",
        ) from exc
    return job
