from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from animedownloader_api.dependencies import get_episode_pipeline_control_service
from animedownloader_api.pipeline_control import (
    EpisodePipelineControlService,
    EpisodePipelineQueueError,
    EpisodePipelineRetryConflictError,
)
from animedownloader_api.schemas import EpisodePipelineRetryResponse

router = APIRouter(prefix="/api/episodes", tags=["episode-pipeline"])

EpisodePipelineControlServiceDependency = Annotated[
    EpisodePipelineControlService,
    Depends(get_episode_pipeline_control_service),
]


@router.post(
    "/{episode_id}/pipeline/retry",
    response_model=EpisodePipelineRetryResponse,
)
async def retry_episode_pipeline(
    episode_id: UUID,
    service: EpisodePipelineControlServiceDependency,
) -> EpisodePipelineRetryResponse:
    try:
        return await service.retry(episode_id)
    except EpisodePipelineRetryConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except EpisodePipelineQueueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
