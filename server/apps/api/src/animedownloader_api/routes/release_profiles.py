from typing import Annotated
from typing import Annotated
from uuid import UUID

from animedownloader_releases import (
    InvalidReleaseParserProfileError,
    ParserField,
    ParserRuleSpec,
    ParserTransform,
    ReleaseGroupNotFoundError,
    ReleaseParserObservationNotFoundError,
    ReleaseParserProfile,
    ReleaseParserProfileActivationError,
    ReleaseParserProfileNotFoundError,
    ReleaseParserSampleNotFoundError,
    ReleaseProfileService,
)
from fastapi import APIRouter, Depends, HTTPException, status

from animedownloader_api.dependencies import get_release_profile_service
from animedownloader_api.release_profile_schemas import (
    ParserComparisonResponse,
    ParserDifferenceResponse,
    ParserHealthResponse,
    ParserSampleResultResponse,
    ParserValidationResponse,
    ReleaseGroupSummaryResponse,
    ReleaseParserObservationResponse,
    ReleaseParserProfileResponse,
    ReleaseParserProfileUpdate,
    ReleaseParserRuleResponse,
    ReleaseParserSampleCreate,
    ReleaseParserSampleResponse,
)
from animedownloader_api.schemas import ParsedReleaseResponse

router = APIRouter(tags=["release-profiles"])
ServiceDependency = Annotated[
    ReleaseProfileService,
    Depends(get_release_profile_service),
]


@router.get("/api/release-groups", response_model=list[ReleaseGroupSummaryResponse])
async def list_release_groups(
    service: ServiceDependency,
) -> list[ReleaseGroupSummaryResponse]:
    groups = await service.list_groups()
    response: list[ReleaseGroupSummaryResponse] = []
    for group in groups:
        active_version = next(
            (
                profile.version
                for profile in reversed(group.parser_profiles)
                if profile.status == "active"
            ),
            None,
        )
        draft_version = next(
            (
                profile.version
                for profile in reversed(group.parser_profiles)
                if profile.status == "draft"
            ),
            None,
        )
        response.append(
            ReleaseGroupSummaryResponse(
                id=group.id,
                name=group.name,
                slug=group.slug,
                enabled=group.enabled,
                active_parser_profile_version=active_version,
                draft_parser_profile_version=draft_version,
            ),
        )
    return response


@router.get(
    "/api/release-groups/{group_id}/parser-profiles",
    response_model=list[ReleaseParserProfileResponse],
)
async def list_parser_profiles(
    group_id: UUID,
    service: ServiceDependency,
) -> list[ReleaseParserProfileResponse]:
    try:
        profiles = await service.list_profiles(group_id)
    except ReleaseGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_profile_response(profile) for profile in profiles]


@router.post(
    "/api/release-groups/{group_id}/parser-profiles/drafts",
    response_model=ReleaseParserProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_parser_draft(
    group_id: UUID,
    service: ServiceDependency,
) -> ReleaseParserProfileResponse:
    try:
        profile = await service.create_draft(group_id)
    except ReleaseGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _profile_response(profile)


@router.get(
    "/api/release-parser-profiles/{profile_id}",
    response_model=ReleaseParserProfileResponse,
)
async def get_parser_profile(
    profile_id: UUID,
    service: ServiceDependency,
) -> ReleaseParserProfileResponse:
    try:
        profile = await service.get_profile(profile_id)
    except ReleaseParserProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _profile_response(profile)


@router.patch(
    "/api/release-parser-profiles/{profile_id}",
    response_model=ReleaseParserProfileResponse,
)
async def update_parser_profile(
    profile_id: UUID,
    payload: ReleaseParserProfileUpdate,
    service: ServiceDependency,
) -> ReleaseParserProfileResponse:
    rules = tuple(
        ParserRuleSpec(
            field=item.field,
            pattern=item.pattern,
            priority=item.priority,
            required=item.required,
            flags=item.flags,
            transform=item.transform,
        )
        for item in payload.rules
    )
    try:
        profile = await service.update_rules(profile_id, rules)
    except ReleaseParserProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidReleaseParserProfileError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _profile_response(profile)


@router.get(
    "/api/release-groups/{group_id}/parser-samples",
    response_model=list[ReleaseParserSampleResponse],
)
async def list_parser_samples(
    group_id: UUID,
    service: ServiceDependency,
) -> list[ReleaseParserSampleResponse]:
    try:
        samples = await service.list_samples(group_id)
    except ReleaseGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [ReleaseParserSampleResponse.model_validate(sample) for sample in samples]


@router.post(
    "/api/release-groups/{group_id}/parser-samples",
    response_model=ReleaseParserSampleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_parser_sample(
    group_id: UUID,
    payload: ReleaseParserSampleCreate,
    service: ServiceDependency,
) -> ReleaseParserSampleResponse:
    try:
        sample = await service.add_sample(
            group_id,
            title=payload.title,
            source=payload.source,
        )
    except ReleaseGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ReleaseParserSampleResponse.model_validate(sample)


@router.delete(
    "/api/release-parser-samples/{sample_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_parser_sample(
    sample_id: UUID,
    service: ServiceDependency,
) -> None:
    try:
        await service.delete_sample(sample_id)
    except ReleaseParserSampleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/api/release-parser-profiles/{profile_id}/validate",
    response_model=ParserValidationResponse,
)
async def validate_parser_profile_endpoint(
    profile_id: UUID,
    service: ServiceDependency,
) -> ParserValidationResponse:
    try:
        result = await service.validate_profile(profile_id)
    except ReleaseParserProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ParserValidationResponse(
        valid=result.valid,
        sample_count=result.sample_count,
        minimum_samples=result.minimum_samples,
        errors=list(result.errors),
        results=[
            ParserSampleResultResponse(
                sample_id=item.sample_id,
                title=item.title,
                parsed=ParsedReleaseResponse.from_parsed(item.parsed)
                if item.parsed is not None
                else None,
                error=item.error,
            )
            for item in result.results
        ],
    )


@router.get(
    "/api/release-parser-profiles/{profile_id}/comparison",
    response_model=ParserComparisonResponse,
)
async def compare_parser_profile(
    profile_id: UUID,
    service: ServiceDependency,
) -> ParserComparisonResponse:
    try:
        result = await service.compare_with_active(profile_id)
    except ReleaseParserProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ParserComparisonResponse(
        profile_id=result.profile_id,
        draft_version=result.draft_version,
        active_version=result.active_version,
        differences=[
            ParserDifferenceResponse(
                sample_id=item.sample_id,
                title=item.title,
                fields={
                    field: [before, after]
                    for field, (before, after) in item.fields.items()
                },
            )
            for item in result.differences
        ],
    )


@router.get(
    "/api/release-parser-profiles/{profile_id}/health",
    response_model=ParserHealthResponse,
)
async def parser_profile_health(
    profile_id: UUID,
    service: ServiceDependency,
) -> ParserHealthResponse:
    try:
        result = await service.health(profile_id)
    except ReleaseParserProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ParserHealthResponse(
        profile_id=result.profile_id,
        total_count=result.total_count,
        parsed_count=result.parsed_count,
        ambiguous_count=result.ambiguous_count,
        unparsed_count=result.unparsed_count,
        unsupported_count=result.unsupported_count,
        failure_rate=result.failure_rate,
        drift_signal=result.drift_signal,
        drift_reason=result.drift_reason,
        recent_failures=[
            ReleaseParserObservationResponse.model_validate(item)
            for item in result.recent_failures
        ],
    )


@router.post(
    "/api/release-parser-profiles/{profile_id}/activate",
    response_model=ReleaseParserProfileResponse,
)
async def activate_parser_profile(
    profile_id: UUID,
    service: ServiceDependency,
) -> ReleaseParserProfileResponse:
    try:
        profile = await service.activate(profile_id)
    except ReleaseParserProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReleaseParserProfileActivationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _profile_response(profile)


@router.post(
    "/api/release-parser-observations/{observation_id}/draft",
    response_model=ReleaseParserProfileResponse,
)
async def create_draft_from_observation(
    observation_id: UUID,
    service: ServiceDependency,
) -> ReleaseParserProfileResponse:
    try:
        profile = await service.create_draft_from_observation(observation_id)
    except ReleaseParserObservationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _profile_response(profile)


def _profile_response(
    profile: ReleaseParserProfile,
) -> ReleaseParserProfileResponse:
    return ReleaseParserProfileResponse(
        id=profile.id,
        release_group_id=profile.release_group_id,
        release_group_name=profile.release_group.name,
        version=profile.version,
        status=profile.status,
        created_at=profile.created_at,
        activated_at=profile.activated_at,
        rules=[
            ReleaseParserRuleResponse(
                id=rule.id,
                field=rule.field,
                pattern=rule.pattern,
                priority=rule.priority,
                required=rule.required,
                flags=rule.flags,
                transform=rule.transform,
            )
            for rule in profile.rules
        ],
    )
