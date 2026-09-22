from uuid import UUID

from animedownloader_anime import Episode, EpisodeUpdateData, AnimeService
from fastapi import APIRouter, Depends, Response, status

from animedownloader_api.dependencies import get_anime_service
from animedownloader_api.schemas import EpisodeResponse, EpisodeUpdate

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: UUID,
    service: AnimeService = Depends(get_anime_service),
) -> Episode:
    return await service.get_episode(episode_id)


@router.patch("/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    episode_id: UUID,
    payload: EpisodeUpdate,
    service: AnimeService = Depends(get_anime_service),
) -> Episode:
    return await service.update_episode(
        episode_id,
        EpisodeUpdateData(
            episode_number=payload.episode_number,
            title=payload.title,
            source=payload.source,
            source_id=payload.source_id,
            source_title=payload.source_title,
            source_url=str(payload.source_url) if payload.source_url is not None else None,
            torrent_url=str(payload.torrent_url) if payload.torrent_url is not None else None,
            size=payload.size,
            seeders=payload.seeders,
            leechers=payload.leechers,
            downloads=payload.downloads,
            info_hash=payload.info_hash,
            download_status=payload.download_status,
            conversion_status=payload.conversion_status,
        ),
    )


@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: UUID,
    service: AnimeService = Depends(get_anime_service),
) -> Response:
    await service.delete_episode(episode_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
