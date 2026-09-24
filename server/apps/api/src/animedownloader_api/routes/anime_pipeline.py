from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from animedownloader_api.dependencies import get_anime_pipeline_service
from animedownloader_api.pipeline import AnimePipelineService
from animedownloader_api.schemas import AnimePipelineResponse

router = APIRouter(prefix="/api/animes", tags=["anime-pipeline"])

AnimePipelineServiceDependency = Annotated[
    AnimePipelineService,
    Depends(get_anime_pipeline_service),
]


@router.get("/{anime_id}/pipeline", response_model=AnimePipelineResponse)
async def get_anime_pipeline(
    anime_id: UUID,
    service: AnimePipelineServiceDependency,
) -> AnimePipelineResponse:
    return await service.get_for_anime(anime_id)
