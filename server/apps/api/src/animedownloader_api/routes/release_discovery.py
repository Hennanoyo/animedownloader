from typing import Annotated
from uuid import UUID

from animedownloader_anime import AnimeService, EpisodeNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query, status

from animedownloader_api.dependencies import (
    get_anime_service,
    get_release_candidate_automation_service,
    get_release_candidate_automation_task_dispatcher,
    get_release_discovery_candidate_acceptance_service,
    get_release_discovery_candidate_service,
    get_release_discovery_scheduler,
    get_release_discovery_service,
)
from animedownloader_api.release_candidate_acceptance import (
    ReleaseCandidateNotAcceptableError,
    ReleaseCandidateReplacementTargetError,
    ReleaseDiscoveryCandidateAcceptanceService,
)
from animedownloader_api.release_candidate_automation import (
    ReleaseAutomationCandidatePreview,
    ReleaseCandidateAutomationService,
)
from animedownloader_api.release_candidates import (
    ReleaseCandidateStatus,
    ReleaseDiscoveryCandidate,
    ReleaseDiscoveryCandidateService,
)
from animedownloader_api.release_discovery import ReleaseDiscoveryService
from animedownloader_api.release_discovery_scheduler import ReleaseDiscoveryScheduler
from animedownloader_api.release_ingestion import (
    ReleaseDoesNotMatchAnimeError,
    ReleaseNotActionableError,
    ReleaseReplacementConflictError,
)
from animedownloader_api.schemas import (
    EpisodeIngestionStatus,
    EpisodeResponse,
    ReleaseAutomationCandidatePreviewResponse,
    ReleaseAutomationPolicyResponse,
    ReleaseAutomationPolicyUpdate,
    ReleaseAutomationRunResponse,
    ReleaseDiscoveryCandidateAcceptanceRequest,
    ReleaseDiscoveryCandidateAcceptanceResponse,
    ReleaseDiscoveryCandidateResponse,
    ReleaseDiscoveryCandidateUpdate,
    ReleaseDiscoveryMatchCandidateResponse,
    ReleaseDiscoveryRunResponse,
    ReleaseDiscoveryScheduleResponse,
    ReleaseDiscoveryScheduleUpdate,
    ReleaseDiscoverySavedSearchPlanResponse,
    ReleaseDiscoverySearchPlanQueryResponse,
    ReleaseDiscoverySearchPlanResponse,
)
from animedownloader_api.task_queue import ReleaseCandidateAutomationTaskDispatcher

router = APIRouter(prefix="/api", tags=["release-discovery"])

AnimeServiceDependency = Annotated[AnimeService, Depends(get_anime_service)]
CandidateServiceDependency = Annotated[
    ReleaseDiscoveryCandidateService,
    Depends(get_release_discovery_candidate_service),
]
DiscoveryServiceDependency = Annotated[
    ReleaseDiscoveryService,
    Depends(get_release_discovery_service),
]
AcceptanceServiceDependency = Annotated[
    ReleaseDiscoveryCandidateAcceptanceService,
    Depends(get_release_discovery_candidate_acceptance_service),
]
SchedulerDependency = Annotated[
    ReleaseDiscoveryScheduler,
    Depends(get_release_discovery_scheduler),
]
AutomationServiceDependency = Annotated[
    ReleaseCandidateAutomationService,
    Depends(get_release_candidate_automation_service),
]
AutomationDispatcherDependency = Annotated[
    ReleaseCandidateAutomationTaskDispatcher,
    Depends(get_release_candidate_automation_task_dispatcher),
]


@router.get(
    "/release-discovery/candidates",
    response_model=list[ReleaseDiscoveryCandidateResponse],
)
async def list_candidates(
    service: CandidateServiceDependency,
    anime_id: UUID | None = None,
    status_filter: Annotated[
        ReleaseCandidateStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ReleaseDiscoveryCandidateResponse]:
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
    service: CandidateServiceDependency,
) -> ReleaseDiscoveryCandidateResponse:
    try:
        next_status = ReleaseCandidateStatus(payload.status)
        candidate = await service.update_candidate_status(
            candidate_id,
            next_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _candidate_response(candidate)


@router.post(
    "/release-discovery/candidates/{candidate_id}/accept",
    response_model=ReleaseDiscoveryCandidateAcceptanceResponse,
)
async def accept_candidate(
    candidate_id: UUID,
    payload: ReleaseDiscoveryCandidateAcceptanceRequest,
    service: AcceptanceServiceDependency,
) -> ReleaseDiscoveryCandidateAcceptanceResponse:
    try:
        result = await service.accept(
            candidate_id,
            replace_episode_id=payload.replace_episode_id,
        )
    except ReleaseCandidateNotAcceptableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EpisodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReleaseCandidateReplacementTargetError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ReleaseDoesNotMatchAnimeError, ReleaseReplacementConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ReleaseNotActionableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ReleaseDiscoveryCandidateAcceptanceResponse(
        status=EpisodeIngestionStatus(result.status.value),
        candidate=_candidate_response(result.candidate),
        episode=(
            EpisodeResponse.model_validate(result.episode)
            if result.episode is not None
            else None
        ),
        existing_episode=(
            EpisodeResponse.model_validate(result.existing_episode)
            if result.existing_episode is not None
            else None
        ),
    )


@router.get(
    "/release-discovery/runs",
    response_model=list[ReleaseDiscoveryRunResponse],
)
async def list_runs(
    service: CandidateServiceDependency,
    anime_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ReleaseDiscoveryRunResponse]:
    runs = await service.list_runs(
        anime_id=anime_id,
        limit=limit,
    )
    return [
        ReleaseDiscoveryRunResponse.model_validate(run, from_attributes=True)
        for run in runs
    ]


@router.get(
    "/animes/{anime_id}/release-automation-policy",
    response_model=ReleaseAutomationPolicyResponse,
)
async def get_automation_policy(
    anime_id: UUID,
    service: AutomationServiceDependency,
) -> ReleaseAutomationPolicyResponse:
    try:
        policy = await service.get_policy(anime_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ReleaseAutomationPolicyResponse.model_validate(policy, from_attributes=True)


@router.patch(
    "/animes/{anime_id}/release-automation-policy",
    response_model=ReleaseAutomationPolicyResponse,
)
async def update_automation_policy(
    anime_id: UUID,
    payload: ReleaseAutomationPolicyUpdate,
    service: AutomationServiceDependency,
) -> ReleaseAutomationPolicyResponse:
    try:
        policy = await service.update_policy(
            anime_id,
            mode=payload.mode,
            min_ranking_score=payload.min_ranking_score,
            require_preference_match=payload.require_preference_match,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ReleaseAutomationPolicyResponse.model_validate(policy, from_attributes=True)


@router.get(
    "/animes/{anime_id}/release-automation-preview",
    response_model=list[ReleaseAutomationCandidatePreviewResponse],
)
async def preview_automation(
    anime_id: UUID,
    service: AutomationServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ReleaseAutomationCandidatePreviewResponse]:
    try:
        previews = await service.preview(anime_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_automation_preview_response(preview) for preview in previews]


@router.post(
    "/animes/{anime_id}/release-automation/run",
    response_model=ReleaseAutomationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_automation(
    anime_id: UUID,
    service: AutomationServiceDependency,
    dispatcher: AutomationDispatcherDependency,
) -> ReleaseAutomationRunResponse:
    try:
        policy = await service.get_policy(anime_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not policy.enabled:
        raise HTTPException(status_code=409, detail="release automation is disabled")
    try:
        await dispatcher.enqueue(anime_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="release automation task could not be queued",
        ) from exc
    return ReleaseAutomationRunResponse(anime_id=anime_id, status="queued")


@router.get(
    "/animes/{anime_id}/release-discovery/plan",
    response_model=ReleaseDiscoverySearchPlanResponse,
)
async def get_discovery_search_plan(
    anime_id: UUID,
    service: DiscoveryServiceDependency,
) -> ReleaseDiscoverySearchPlanResponse:
    try:
        plan, search_profile_version = await service.build_anime_search_plan(anime_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ReleaseDiscoverySearchPlanResponse(
        anime_id=anime_id,
        query_budget=len(plan.queries),
        search_profile_version=search_profile_version,
        queries=[
            ReleaseDiscoverySearchPlanQueryResponse(
                position=index,
                query=query.query,
                fields=[field.value for field in query.fields],
            )
            for index, query in enumerate(plan.queries, start=1)
        ],
    )


@router.get(
    "/animes/{anime_id}/release-discovery-schedule",
    response_model=ReleaseDiscoveryScheduleResponse,
)
async def get_schedule(
    anime_id: UUID,
    anime_service: AnimeServiceDependency,
    service: CandidateServiceDependency,
) -> ReleaseDiscoveryScheduleResponse:
    await anime_service.get_anime(anime_id)
    schedule = await service.get_schedule(anime_id)
    return _schedule_response(schedule)


@router.patch(
    "/animes/{anime_id}/release-discovery-schedule",
    response_model=ReleaseDiscoveryScheduleResponse,
)
async def update_schedule(
    anime_id: UUID,
    payload: ReleaseDiscoveryScheduleUpdate,
    service: CandidateServiceDependency,
) -> ReleaseDiscoveryScheduleResponse:
    plan = payload.search_plan
    try:
        schedule = await service.update_schedule(
            anime_id,
            enabled=payload.enabled,
            interval_minutes=payload.interval_minutes,
            search_title_source=plan.title_source if plan else None,
            search_title=plan.title if plan else None,
            search_field_order=plan.field_order if plan else None,
            search_enabled_fields=plan.enabled_fields if plan else None,
            search_group=plan.group if plan else None,
            search_episode=plan.episode if plan else None,
            search_resolution=plan.resolution if plan else None,
            search_codec=plan.codec if plan else None,
            search_source=plan.source if plan else None,
            automation_mode=payload.automation_mode,
            automation_min_ranking_score=payload.automation_min_ranking_score,
            automation_require_plan_match=payload.automation_require_plan_match,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _schedule_response(schedule)


@router.post(
    "/animes/{anime_id}/release-discovery/run",
    response_model=ReleaseDiscoveryRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_discovery_now(
    anime_id: UUID,
    service: CandidateServiceDependency,
    scheduler: SchedulerDependency,
) -> ReleaseDiscoveryRunResponse:
    schedule = await service.get_schedule(anime_id)
    if (
        not getattr(schedule, "search_title", None)
        or not getattr(schedule, "search_field_order", None)
        or not getattr(schedule, "search_enabled_fields", None)
    ):
        raise HTTPException(
            status_code=409,
            detail="save a Search Plan in Find releases before running discovery",
        )

    run = await service.create_manual_run(anime_id)

    if run.status == "queued":
        try:
            await scheduler.enqueue_run(run.id)
        except Exception as exc:
            await service.fail_run(
                run.id,
                f"Failed to enqueue discovery task: {type(exc).__name__}: {exc}",
            )
            raise HTTPException(
                status_code=503,
                detail="Release discovery task could not be queued",
            ) from exc

    return ReleaseDiscoveryRunResponse.model_validate(run, from_attributes=True)


def _schedule_response(
    schedule: object,
) -> ReleaseDiscoveryScheduleResponse:
    search_plan = None
    title = getattr(schedule, "search_title", None)
    field_order = getattr(schedule, "search_field_order", None)
    enabled_fields = getattr(schedule, "search_enabled_fields", None)
    if title and field_order and enabled_fields:
        search_plan = ReleaseDiscoverySavedSearchPlanResponse(
            title_source=getattr(schedule, "search_title_source", None) or "custom",
            title=title,
            field_order=list(field_order),
            enabled_fields=list(enabled_fields),
            group=getattr(schedule, "search_group", None),
            episode=getattr(schedule, "search_episode", None),
            resolution=getattr(schedule, "search_resolution", None),
            codec=getattr(schedule, "search_codec", None),
            source=getattr(schedule, "search_source", None),
        )
    return ReleaseDiscoveryScheduleResponse(
        anime_id=getattr(schedule, "anime_id"),
        enabled=getattr(schedule, "enabled"),
        interval_minutes=getattr(schedule, "interval_minutes"),
        next_run_at=getattr(schedule, "next_run_at"),
        last_run_at=getattr(schedule, "last_run_at"),
        last_run_status=getattr(schedule, "last_run_status"),
        search_plan=search_plan,
        automation_mode=getattr(schedule, "automation_mode", "off"),
        automation_min_ranking_score=getattr(schedule, "automation_min_ranking_score", 0),
        automation_require_plan_match=getattr(
            schedule,
            "automation_require_plan_match",
            True,
        ),
    )


def _automation_preview_response(
    preview: ReleaseAutomationCandidatePreview,
) -> ReleaseAutomationCandidatePreviewResponse:
    return ReleaseAutomationCandidatePreviewResponse(
        candidate=_candidate_response(preview.candidate),
        eligible=preview.eligible,
        reasons=list(preview.reasons),
        automation_status=preview.candidate.automation_status or "idle",
    )


def _candidate_response(candidate: ReleaseDiscoveryCandidate) -> ReleaseDiscoveryCandidateResponse:
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
        automation_status=candidate.automation_status or "idle",
        automation_claimed_at=candidate.automation_claimed_at,
        automation_completed_at=candidate.automation_completed_at,
        automation_error=candidate.automation_error,
    )
