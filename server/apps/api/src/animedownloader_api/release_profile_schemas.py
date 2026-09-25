from datetime import datetime
from datetime import datetime
from uuid import UUID

from animedownloader_releases import ParserField, ParserTransform
from pydantic import BaseModel, ConfigDict, Field

from animedownloader_api.schemas import ParsedReleaseResponse


class ReleaseGroupSummaryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    enabled: bool
    active_parser_profile_version: int | None
    draft_parser_profile_version: int | None


class ReleaseParserRuleInput(BaseModel):
    field: ParserField
    pattern: str = Field(min_length=1, max_length=2000)
    priority: int = Field(ge=0, le=100000)
    required: bool = False
    flags: str = Field(default="", max_length=32)
    transform: ParserTransform = ParserTransform.IDENTITY


class ReleaseParserRuleResponse(ReleaseParserRuleInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class ReleaseParserProfileResponse(BaseModel):
    id: UUID
    release_group_id: UUID
    release_group_name: str
    version: int
    status: str
    created_at: datetime
    activated_at: datetime | None
    rules: list[ReleaseParserRuleResponse]


def _empty_parser_rules() -> list[ReleaseParserRuleInput]:
    return []


class ReleaseParserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules: list[ReleaseParserRuleInput] = Field(default_factory=_empty_parser_rules)


class ReleaseParserSampleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    source: str = Field(default="nyaa", min_length=1, max_length=32)


class ReleaseParserSampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    release_group_id: UUID
    source: str
    title: str
    created_at: datetime
    updated_at: datetime


class ReleaseParserObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    release_group_id: UUID
    profile_id: UUID
    source: str
    title: str
    status: str
    failed_required_fields: list[str]
    observed_at: datetime


class ParserSampleResultResponse(BaseModel):
    sample_id: UUID
    title: str
    parsed: ParsedReleaseResponse | None
    error: str | None


class ParserValidationResponse(BaseModel):
    valid: bool
    sample_count: int
    minimum_samples: int
    errors: list[str]
    results: list[ParserSampleResultResponse]


class ParserDifferenceResponse(BaseModel):
    sample_id: UUID
    title: str
    fields: dict[str, list[object]]


class ParserComparisonResponse(BaseModel):
    profile_id: UUID
    draft_version: int
    active_version: int | None
    differences: list[ParserDifferenceResponse]


class ParserHealthResponse(BaseModel):
    profile_id: UUID
    total_count: int
    parsed_count: int
    ambiguous_count: int
    unparsed_count: int
    unsupported_count: int
    failure_rate: float
    drift_signal: bool
    drift_reason: str | None
    recent_failures: list[ReleaseParserObservationResponse]
