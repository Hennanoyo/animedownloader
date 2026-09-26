from typing import Annotated
from uuid import UUID

from animedownloader_anime import AnimeService
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from animedownloader_api.dependencies import get_anime_service, get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from animedownloader_api.release_candidates import (
    ReleaseCandidateStatus,
    ReleaseDiscoveryCandidateService,
)
from animedownloader_api.schemas import (
    ReleaseDiscoveryCandidateResponse,
    ReleaseDiscoveryCandidateUpdate,
    ReleaseDiscoveryMatchCandidateResponse,
    ReleaseDiscoveryRunResponse,
    ReleaseDiscoveryScheduleResponse,
    ReleaseDiscoveryScheduleUpdate,
)
from animedownloader_api.release_discovery_scheduler import ReleaseDiscoveryScheduler

router = APIRouter(prefix="/api", tags=["release-discovery"])

SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
AnimeServiceDependency = Annotated[AnimeService, Depends(get_anime_service)]


@router.get(
    "/release-discovery/candidates",
    response_model=list[ReleaseDiscoveryCandidateResponse],
)
async def list_candidates(
    session: SessionDependency,
    anime_id: UUID | None = None,
    status_filter: Annotated[
        ReleaseCandidateStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ReleaseDiscoveryCandidateResponse]:
    service = ReleaseDiscoveryCandidateService(session)
    candidates = await service.list_candidates(
        anime_id=anime_id,
        status=status_filter,
        limit=limit,
    )
    return [_candidate_response(candidate) for candidate in candidates]


@router.patch(
    "/release-discovery/candidates/{candidate_id}",
    response_model=ReleaseDiscoveryCandidateResponse,
)
async def update_candidate(
    candidate_id: UUID,
    payload: ReleaseDiscoveryCandidateUpdate,
    session: SessionDependency,
) -> ReleaseDiscoveryCandidateResponse:
    try:
        next_status = ReleaseCandidateStatus(payload.status)
        candidate = await ReleaseDiscoveryCandidateService(session).update_candidate_status(
            candidate_id,
            next_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _candidate_response(candidate)


@router.get(
    "/release-discovery/runs",
    response_model=list[ReleaseDiscoveryRunResponse],
)
async def list_runs(
    session: SessionDependency,
    anime_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ReleaseDiscoveryRunResponse]:
    runs = await ReleaseDiscoveryCandidateService(session).list_runs(
        anime_id=anime_id,
        limit=limit,
    )
    return [
        ReleaseDiscoveryRunResponse.model_validate(run, from_attributes=True)
        for run in runs
    ]


@router.get(
    "/animes/{anime_id}/release-discovery-schedule",
    response_model=ReleaseDiscoveryScheduleResponse,
)
async def get_schedule(
    anime_id: UUID,
    anime_service: AnimeServiceDependency,
    session: SessionDependency,
) -> ReleaseDiscoveryScheduleResponse:
    await anime_service.get_anime(anime_id)
    schedule = await ReleaseDiscoveryCandidateService(session).get_schedule(anime_id)
    return ReleaseDiscoveryScheduleResponse.model_validate(schedule, from_attributes=True)


@router.patch(
    "/animes/{anime_id}/release-discovery-schedule",
    response_model=ReleaseDiscoveryScheduleResponse,
)
async def update_schedule(
    anime_id: UUID,
    payload: ReleaseDiscoveryScheduleUpdate,
    anime_service: AnimeServiceDependency,
    session: SessionDependency,
) -> ReleaseDiscoveryScheduleResponse:
    await anime_service.get_anime(anime_id)
    try:
        schedule = await ReleaseDiscoveryCandidateService(session).update_schedule(
            anime_id,
            enabled=payload.enabled,
            interval_minutes=payload.interval_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ReleaseDiscoveryScheduleResponse.model_validate(schedule, from_attributes=True)


@router.post(
    "/animes/{anime_id}/release-discovery/run",
    response_model=ReleaseDiscoveryRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_discovery_now(
    anime_id: UUID,
    request: Request,
    anime_service: AnimeServiceDependency,
    session: SessionDependency,
) -> ReleaseDiscoveryRunResponse:
    await anime_service.get_anime(anime_id)
    run = await ReleaseDiscoveryCandidateService(session).create_manual_run(anime_id)
    scheduler = request.app.state.release_discovery_scheduler
    assert isinstance(scheduler, ReleaseDiscoveryScheduler)

    if run.status == "queued":
        try:
            await scheduler.enqueue_run(run.id)
        except Exception as exc:
            await ReleaseDiscoveryCandidateService(session).fail_run(
                run.id,
                f"Failed to enqueue discovery task: {type(exc).__name__}: {exc}",
            )
            raise HTTPException(
                status_code=503,
                detail="Release discovery task could not be queued",
            ) from exc

    return ReleaseDiscoveryRunResponse.model_validate(run, from_attributes=True)


def _candidate_response(candidate: object) -> ReleaseDiscoveryCandidateResponse:
    return ReleaseDiscoveryCandidateResponse(
        id=candidate.id,
        anime_id=candidate.anime_id,
        last_run_id=candidate.last_run_id,
        provider_source=candidate.provider_source,
        source_id=candidate.source_id,
        source_title=candidate.source_title,
        page_url=candidate.page_url,
        torrent_url=candidate.torrent_url,
        published_at=candidate.published_at,
        size=candidate.size,
        seeders=candidate.seeders,
        leechers=candidate.leechers,
        downloads=candidate.downloads,
        info_hash=candidate.info_hash,
        normalized_title=candidate.normalized_title,
        release_group=candidate.release_group,
        series_title=candidate.series_title,
        episode_number=candidate.episode_number,
        episode_title=candidate.episode_title,
        season_number=candidate.season_number,
        resolution=candidate.resolution,
        source=candidate.source,
        video_codec=candidate.video_codec,
        audio_codec=candidate.audio_codec,
        bit_depth=candidate.bit_depth,
        parse_status=candidate.parse_status,
        parse_warnings=list(candidate.parse_warnings),
        failed_required_fields=list(candidate.failed_required_fields),
        parser_profile_version=candidate.parser_profile_version,
        normalized_series_title=candidate.normalized_series_title,
        match_status=candidate.match_status,
        match_candidates=[
            ReleaseDiscoveryMatchCandidateResponse.model_validate(item)
            for item in candidate.match_candidates
        ],
        ranking_score=candidate.ranking_score,
        ranking_reasons=list(candidate.ranking_reasons),
        status=candidate.status,
        first_seen_at=candidate.first_seen_at,
        last_seen_at=candidate.last_seen_at,
        reviewed_at=candidate.reviewed_at,
    )
