from typing import Annotated
from uuid import UUID

from animedownloader_anime import AnimeNotFoundError, EpisodeNotFoundError
from animedownloader_nyaa import NyaaClient, NyaaError
from animedownloader_releases import AnimeMatchResult, Release, SearchField
from fastapi import APIRouter, Depends, HTTPException, Query

from animedownloader_api.dependencies import (
    get_nyaa_client,
    get_release_discovery_service,
    get_release_ingestion_service,
)
from animedownloader_api.release_discovery import ReleaseDiscoveryService
from animedownloader_api.release_ingestion import (
    EpisodeIngestionResult,
    EpisodeIngestionService,
    ReleaseDoesNotMatchAnimeError,
    ReleaseNotActionableError,
    ReleaseReplacementConflictError,
)
from animedownloader_api.schemas import (
    AnimeMatchCandidateResponse,
    AnimeMatchResponse,
    EpisodeIngestionRequest,
    EpisodeIngestionResponse,
    EpisodeReleaseReplacementRequest,
    EpisodeResponse,
    ParsedReleaseResponse,
    ReleaseDiscoveryItemResponse,
    ReleaseDiscoveryResponse,
    ReleaseRankingResponse,
    ReleaseResponse,
    ReleaseSearchResponse,
)

router = APIRouter(prefix="/api/releases", tags=["releases"])


@router.get("/search", response_model=ReleaseSearchResponse)
async def search_releases(
    query: Annotated[str, Query(alias="q", min_length=1, max_length=200)],
    client: Annotated[NyaaClient, Depends(get_nyaa_client)],
) -> ReleaseSearchResponse:
    normalized_query = query.strip()
    if not normalized_query:
        raise HTTPException(status_code=422, detail="Search query must not be empty")

    try:
        search_result = await client.search(normalized_query)
    except NyaaError as exc:
        raise HTTPException(
            status_code=502,
            detail="Nyaa search is temporarily unavailable",
        ) from exc

    return ReleaseSearchResponse(
        query=normalized_query,
        items=[
            ReleaseResponse.model_validate(release)
            for release in search_result.items
        ],
    )


ReleaseDiscoveryServiceDependency = Annotated[
    ReleaseDiscoveryService,
    Depends(get_release_discovery_service),
]


@router.get("/discover", response_model=ReleaseDiscoveryResponse)
async def discover_releases(
    title: Annotated[str, Query(min_length=1, max_length=200)],
    service: ReleaseDiscoveryServiceDependency,
    group: Annotated[str | None, Query(max_length=128)] = None,
    anime_id: UUID | None = None,
    episode: Annotated[int | None, Query(ge=1, le=9999)] = None,
    resolution: Annotated[str | None, Query(max_length=32)] = None,
    codec: Annotated[str | None, Query(max_length=32)] = None,
    fields: Annotated[list[SearchField] | None, Query()] = None,
) -> ReleaseDiscoveryResponse:
    normalized_title = title.strip()
    if not normalized_title:
        raise HTTPException(status_code=422, detail="Search title must not be empty")

    result = await service.discover(
        title=normalized_title,
        anime_id=anime_id,
        group=group.strip() if group else None,
        episode=episode,
        resolution=resolution.strip() if resolution else None,
        codec=codec.strip() if codec else None,
        fields=tuple(fields) if fields else None,
    )
    return ReleaseDiscoveryResponse(
        query=result.query,
        queries=list(result.queries),
        warnings=list(result.warnings),
        search_profile_version=result.search_profile_version,
        items=[
            ReleaseDiscoveryItemResponse(
                release=ReleaseResponse.model_validate(item.release),
                parsed=ParsedReleaseResponse.from_parsed(item.parsed),
                match=_match_response(item.match),
                ranking=ReleaseRankingResponse(
                    score=item.ranking.score,
                    reasons=list(item.ranking.reasons),
                ),
            )
            for item in result.items
        ],
    )


EpisodeIngestionServiceDependency = Annotated[
    EpisodeIngestionService,
    Depends(get_release_ingestion_service),
]


@router.post(
    "/ingest",
    response_model=EpisodeIngestionResponse,
)
async def ingest_release(
    payload: EpisodeIngestionRequest,
    service: EpisodeIngestionServiceDependency,
) -> EpisodeIngestionResponse:
    try:
        result = await service.ingest(
            anime_id=payload.anime_id,
            release=_release_from_response(payload.release),
            parsed=payload.parsed.to_parsed(),
        )
    except ReleaseNotActionableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ReleaseDoesNotMatchAnimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return _ingestion_response(result)


@router.post(
    "/episodes/{episode_id}/replace",
    response_model=EpisodeIngestionResponse,
)
async def replace_episode_release(
    episode_id: UUID,
    payload: EpisodeReleaseReplacementRequest,
    service: EpisodeIngestionServiceDependency,
) -> EpisodeIngestionResponse:
    try:
        result = await service.replace(
            episode_id=episode_id,
            release=_release_from_response(payload.release),
            parsed=payload.parsed.to_parsed(),
        )
    except (AnimeNotFoundError, EpisodeNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        ReleaseDoesNotMatchAnimeError,
        ReleaseReplacementConflictError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ReleaseNotActionableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _ingestion_response(result)


def _match_response(match: AnimeMatchResult) -> AnimeMatchResponse:
    return AnimeMatchResponse(
        status=match.status.value,
        normalized_series_title=match.normalized_series_title,
        candidates=[
            AnimeMatchCandidateResponse(
                anime_id=candidate.anime_id,
                title=candidate.title,
                matched_titles=list(candidate.matched_titles),
            )
            for candidate in match.candidates
        ],
    )


def _release_from_response(payload: ReleaseResponse) -> Release:
    return Release(
        source=payload.source,
        id=payload.id,
        title=payload.title,
        page_url=payload.page_url,
        torrent_url=payload.torrent_url,
        published_at=payload.published_at,
        size=payload.size,
        seeders=payload.seeders,
        leechers=payload.leechers,
        downloads=payload.downloads,
        info_hash=payload.info_hash,
    )


def _ingestion_response(
    result: EpisodeIngestionResult,
) -> EpisodeIngestionResponse:
    return EpisodeIngestionResponse.model_validate(
        {
            "status": result.status.value,
            "episode": (
                EpisodeResponse.model_validate(result.episode)
                if result.episode is not None
                else None
            ),
            "existing_episode": (
                EpisodeResponse.model_validate(result.existing_episode)
                if result.existing_episode is not None
                else None
            ),
        },
    )
