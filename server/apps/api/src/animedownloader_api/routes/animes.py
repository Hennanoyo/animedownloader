from typing import Annotated
from uuid import UUID

from animedownloader_anime import (
    Anime,
    AnimeCreateData,
    AnimeService,
    AnimeUpdateData,
    Episode,
    EpisodeCreateData,
)
from fastapi import APIRouter, Depends, Response, status

from animedownloader_api.dependencies import get_anime_service
from animedownloader_api.schemas import (
    AnimeCreate,
    AnimeResponse,
    AnimeUpdate,
    EpisodeCreate,
)

router = APIRouter(prefix="/api/animes", tags=["animes"])
AnimeServiceDependency = Annotated[AnimeService, Depends(get_anime_service)]


@router.get("", response_model=list[AnimeResponse])
async def list_animes(service: AnimeServiceDependency) -> list[Anime]:
    return await service.list_animes()


@router.post("", response_model=AnimeResponse, status_code=status.HTTP_201_CREATED)
async def create_anime(
    payload: AnimeCreate,
    service: AnimeServiceDependency,
) -> Anime:
    return await service.create_anime(_to_anime_create_data(payload))


@router.get("/{anime_id}", response_model=AnimeResponse)
async def get_anime(
    anime_id: UUID,
    service: AnimeServiceDependency,
) -> Anime:
    return await service.get_anime(anime_id)


@router.patch("/{anime_id}", response_model=AnimeResponse)
async def update_anime(
    anime_id: UUID,
    payload: AnimeUpdate,
    service: AnimeServiceDependency,
) -> Anime:
    return await service.update_anime(
        anime_id,
        AnimeUpdateData(
            title=payload.title,
            year=payload.year,
            season=payload.season,
            weekday=payload.weekday,
            air_time=payload.air_time,
            timezone=payload.timezone,
        ),
    )


@router.delete("/{anime_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_anime(
    anime_id: UUID,
    service: AnimeServiceDependency,
) -> Response:
    await service.delete_anime(anime_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{anime_id}/episodes", response_model=list[EpisodeResponse])
async def list_episodes(
    anime_id: UUID,
    service: AnimeServiceDependency,
) -> list[Episode]:
    return await service.list_episodes(anime_id)


@router.post(
    "/{anime_id}/episodes",
    response_model=EpisodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_episode(
    anime_id: UUID,
    payload: EpisodeCreate,
    service: AnimeServiceDependency,
) -> Episode:
    return await service.create_episode(
        anime_id,
        _to_episode_create_data(payload),
    )


def _to_anime_create_data(payload: AnimeCreate) -> AnimeCreateData:
    return AnimeCreateData(
        title=payload.title,
        year=payload.year,
        season=payload.season,
        weekday=payload.weekday,
        air_time=payload.air_time,
        timezone=payload.timezone,
        episodes=tuple(
            _to_episode_create_data(episode)
            for episode in payload.episodes
        ),
    )


def _to_episode_create_data(payload: EpisodeCreate) -> EpisodeCreateData:
    return EpisodeCreateData(
        episode_number=payload.episode_number,
        title=payload.title,
        source=payload.source,
        source_id=payload.source_id,
        source_title=payload.source_title,
        source_url=str(payload.source_url) if payload.source_url is not None else None,
        torrent_url=str(payload.torrent_url),
        size=payload.size,
        seeders=payload.seeders,
        leechers=payload.leechers,
        downloads=payload.downloads,
        info_hash=payload.info_hash,
        download_status=payload.download_status,
        conversion_status=payload.conversion_status,
    )
