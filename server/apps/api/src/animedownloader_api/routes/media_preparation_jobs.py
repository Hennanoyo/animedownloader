from typing import Annotated
from uuid import UUID

from animedownloader_media_asset import MediaAssetService
from animedownloader_media_processing import (
    MediaPreparationJob,
    MediaPreparationJobService,
)
from fastapi import APIRouter, Depends, HTTPException, status

from animedownloader_api.dependencies import (
    get_media_asset_service,
    get_media_preparation_job_service,
    get_media_processing_task_dispatcher,
)
from animedownloader_api.media_processing_queue import MediaProcessingTaskDispatcher
from animedownloader_api.schemas import MediaPreparationJobResponse

router = APIRouter(
    prefix="/api/media-preparation-jobs",
    tags=["media-preparation-jobs"],
)

MediaPreparationJobServiceDependency = Annotated[
    MediaPreparationJobService,
    Depends(get_media_preparation_job_service),
]
MediaAssetServiceDependency = Annotated[
    MediaAssetService,
    Depends(get_media_asset_service),
]
MediaProcessingTaskDispatcherDependency = Annotated[
    MediaProcessingTaskDispatcher,
    Depends(get_media_processing_task_dispatcher),
]


@router.get("/{job_id}", response_model=MediaPreparationJobResponse)
async def get_media_preparation_job(
    job_id: UUID,
    service: MediaPreparationJobServiceDependency,
) -> MediaPreparationJob:
    return await service.get_job(job_id)


@router.post(
    "/{job_id}/retry",
    response_model=MediaPreparationJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def retry_media_preparation_job(
    job_id: UUID,
    service: MediaPreparationJobServiceDependency,
    asset_service: MediaAssetServiceDependency,
    dispatcher: MediaProcessingTaskDispatcherDependency,
) -> MediaPreparationJob:
    job = await service.get_job(job_id)
    if job.status in {"pending", "processing"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Media preparation job is already active",
        )

    asset = await asset_service.get(job.media_asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset not found",
        )
    if asset.metadata_updated_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Media asset metadata is not ready",
        )

    new_job = await service.create_job(
        media_asset_id=asset.id,
        source_path=asset.path,
        source_metadata_updated_at=asset.metadata_updated_at,
        thumbnail_ready=asset.thumbnail_ready,
    )
    if new_job is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A current or active media preparation job already exists",
        )

    try:
        await dispatcher.enqueue_preparation(new_job.id)
    except Exception as exc:
        await service.mark_failed(
            new_job.id,
            error_message="Failed to enqueue media preparation task.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media preparation task queue is temporarily unavailable",
        ) from exc

    return new_job
