from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from animedownloader_api.dependencies import get_media_source_service
from animedownloader_api.media_source import (
    MediaSourceRecoveryConflictError,
    MediaSourceRecoveryError,
    MediaSourceService,
)
from animedownloader_api.schemas import (
    EpisodeMediaSourceResponse,
    EpisodeMediaSourceStatus,
    EpisodePipelineCurrentStage,
    EpisodePipelineRetryResponse,
    EpisodePipelineStageStatus,
    MediaSourceCandidateResponse,
    MediaSourceOrphanResponse,
    MediaSourceSelectionRequest,
)

router = APIRouter(prefix="/api", tags=["media-source"])

MediaSourceServiceDependency = Annotated[
    MediaSourceService,
    Depends(get_media_source_service),
]


@router.get(
    "/episodes/{episode_id}/media-source",
    response_model=EpisodeMediaSourceResponse,
)
async def get_episode_media_source(
    episode_id: UUID,
    service: MediaSourceServiceDependency,
) -> EpisodeMediaSourceResponse:
    source = await service.get_episode_source(episode_id)
    return EpisodeMediaSourceResponse(
        episode_id=source.episode_id,
        download_job_id=source.download_job_id,
        download_status=source.download_status,
        status=EpisodeMediaSourceStatus(source.status),
        root=source.root,
        selected_path=source.selected_path,
        candidates=[
            MediaSourceCandidateResponse(path=candidate.path)
            for candidate in source.candidates
        ],
        processing_job_id=source.processing_job_id,
        processing_status=source.processing_status,
    )


@router.post(
    "/episodes/{episode_id}/media-source/reprocess",
    response_model=EpisodePipelineRetryResponse,
)
async def reprocess_episode_media_source(
    episode_id: UUID,
    service: MediaSourceServiceDependency,
) -> EpisodePipelineRetryResponse:
    try:
        job = await service.reprocess(episode_id)
    except MediaSourceRecoveryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except MediaSourceRecoveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return EpisodePipelineRetryResponse(
        stage=EpisodePipelineCurrentStage.PROCESSING,
        job_id=job.id,
        status=EpisodePipelineStageStatus.PENDING,
    )


@router.post(
    "/episodes/{episode_id}/media-source/redownload",
    response_model=EpisodePipelineRetryResponse,
)
async def redownload_episode_media_source(
    episode_id: UUID,
    service: MediaSourceServiceDependency,
) -> EpisodePipelineRetryResponse:
    try:
        job = await service.redownload(episode_id)
    except MediaSourceRecoveryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except MediaSourceRecoveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return EpisodePipelineRetryResponse(
        stage=EpisodePipelineCurrentStage.DOWNLOAD,
        job_id=job.id,
        status=EpisodePipelineStageStatus.PENDING,
    )


@router.post(
    "/episodes/{episode_id}/media-source/select",
    response_model=EpisodePipelineRetryResponse,
)
async def select_episode_media_source(
    episode_id: UUID,
    payload: MediaSourceSelectionRequest,
    service: MediaSourceServiceDependency,
) -> EpisodePipelineRetryResponse:
    try:
        job = await service.select_source(episode_id, payload.path)
    except MediaSourceRecoveryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except MediaSourceRecoveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return EpisodePipelineRetryResponse(
        stage=EpisodePipelineCurrentStage.PROCESSING,
        job_id=job.id,
        status=EpisodePipelineStageStatus.PENDING,
    )


@router.get(
    "/media-sources/orphans",
    response_model=list[MediaSourceOrphanResponse],
)
async def list_media_source_orphans(
    service: MediaSourceServiceDependency,
) -> list[MediaSourceOrphanResponse]:
    return [
        MediaSourceOrphanResponse(
            directory_id=item.directory_id,
            path=item.path,
        )
        for item in await service.list_orphans()
    ]


@router.delete("/media-sources/orphans/{directory_id}", status_code=204)
async def delete_media_source_orphan(
    directory_id: UUID,
    service: MediaSourceServiceDependency,
) -> None:
    try:
        await service.delete_orphan(directory_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MediaSourceRecoveryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


__all__ = ["router"]
