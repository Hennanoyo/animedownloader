from typing import Annotated
from uuid import UUID

from animedownloader_media_processing import (
    MediaPackagingJob,
    MediaStreamingPackageService,
    MediaVariantService,
)
from fastapi import APIRouter, Depends, HTTPException, status

from animedownloader_api.dependencies import (
    get_media_streaming_package_service,
    get_media_processing_task_dispatcher,
    get_media_variant_service,
)
from animedownloader_api.media_processing_queue import MediaProcessingTaskDispatcher
from animedownloader_api.schemas import MediaPackagingJobResponse

router = APIRouter(
    prefix="/api/media-packaging-jobs",
    tags=["media-packaging-jobs"],
)

MediaStreamingPackageServiceDependency = Annotated[
    MediaStreamingPackageService,
    Depends(get_media_streaming_package_service),
]
MediaVariantServiceDependency = Annotated[
    MediaVariantService,
    Depends(get_media_variant_service),
]
MediaProcessingTaskDispatcherDependency = Annotated[
    MediaProcessingTaskDispatcher,
    Depends(get_media_processing_task_dispatcher),
]


@router.get("/{job_id}", response_model=MediaPackagingJobResponse)
async def get_media_packaging_job(
    job_id: UUID,
    service: MediaStreamingPackageServiceDependency,
) -> MediaPackagingJob:
    return await service.get_job(job_id)


@router.post(
    "/{job_id}/retry",
    response_model=MediaPackagingJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def retry_media_packaging_job(
    job_id: UUID,
    service: MediaStreamingPackageServiceDependency,
    variant_service: MediaVariantServiceDependency,
    dispatcher: MediaProcessingTaskDispatcherDependency,
) -> MediaPackagingJob:
    job = await service.get_job(job_id)
    if job.status in {"pending", "processing"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Media packaging job is already active",
        )

    variant = await variant_service.get_playable_variant(job.media_variant_id)
    if variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playable media variant not found",
        )

    new_job = await service.create_job(media_variant_id=variant.id)
    if new_job is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A current or active media packaging job already exists",
        )

    try:
        await dispatcher.enqueue_packaging(new_job.id)
    except Exception as exc:
        await service.mark_failed(
            new_job.id,
            error_message="Failed to enqueue media packaging task.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media packaging task queue is temporarily unavailable",
        ) from exc

    return new_job
