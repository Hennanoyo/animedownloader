from datetime import datetime, time
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from animedownloader_anime import ConversionStatus, DownloadStatus, Season, Weekday
from animedownloader_download import DownloadJobStatus, MediaSourceStatus
from animedownloader_media_asset import (
    MediaAttachmentStatus,
    MediaThumbnailStatus,
    SubtitleTrackStatus,
)
from animedownloader_media_processing import (
    MediaPackagingJobStatus,
    MediaPreparationJobStatus,
    MediaProcessingJobStatus,
    MediaStreamingPackageStatus,
    MediaStreamingRepresentationStatus,
    MediaTranscodingOperation,
    MediaVariantKind,
    MediaVariantStatus,
)
from animedownloader_releases import ParsedRelease
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints


class ReleaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    id: str
    title: str
    page_url: str
    torrent_url: str
    published_at: datetime | None
    size: str | None
    seeders: int | None
    leechers: int | None
    downloads: int | None
    info_hash: str | None


class ReleaseSearchResponse(BaseModel):
    query: str
    items: list[ReleaseResponse]


class ParsedReleaseResponse(BaseModel):
    provider_source: str
    source_id: str
    original_title: str
    normalized_title: str
    release_group: str | None
    series_title: str | None
    episode_number: int | None
    episode_title: str | None
    season_number: int | None
    resolution: str | None
    source: str | None
    video_codec: str | None
    audio_codec: str | None
    bit_depth: int | None
    status: str
    warnings: list[str]
    failed_required_fields: list[str]
    parser_profile_version: int | None

    @classmethod
    def from_parsed(cls, parsed: ParsedRelease) -> ParsedReleaseResponse:
        return cls(
            provider_source=parsed.provider_source,
            source_id=parsed.source_id,
            original_title=parsed.original_title,
            normalized_title=parsed.normalized_title,
            release_group=parsed.release_group,
            series_title=parsed.series_title,
            episode_number=parsed.episode_number,
            episode_title=parsed.episode_title,
            season_number=parsed.season_number,
            resolution=parsed.resolution,
            source=parsed.source,
            video_codec=parsed.video_codec,
            audio_codec=parsed.audio_codec,
            bit_depth=parsed.bit_depth,
            status=parsed.status.value,
            warnings=list(parsed.warnings),
            failed_required_fields=[field.value for field in parsed.failed_required_fields],
            parser_profile_version=parsed.parser_profile_version,
        )
    def to_parsed(self) -> ParsedRelease:
        from animedownloader_releases import ParserField, ParseStatus

        return ParsedRelease(
            provider_source=self.provider_source,
            source_id=self.source_id,
            original_title=self.original_title,
            normalized_title=self.normalized_title,
            release_group=self.release_group,
            series_title=self.series_title,
            episode_number=self.episode_number,
            episode_title=self.episode_title,
            season_number=self.season_number,
            resolution=self.resolution,
            source=self.source,
            video_codec=self.video_codec,
            audio_codec=self.audio_codec,
            bit_depth=self.bit_depth,
            status=ParseStatus(self.status),
            warnings=tuple(self.warnings),
            failed_required_fields=tuple(
                ParserField(field) for field in self.failed_required_fields
            ),
            parser_profile_version=self.parser_profile_version,
        )



class AnimeMatchCandidateResponse(BaseModel):
    anime_id: UUID
    title: str
    matched_titles: list[str]


class AnimeMatchResponse(BaseModel):
    status: str
    normalized_series_title: str | None
    candidates: list[AnimeMatchCandidateResponse]


class ReleaseRankingResponse(BaseModel):
    score: int = Field(ge=0)
    reasons: list[str]


class ReleaseDiscoveryItemResponse(BaseModel):
    release: ReleaseResponse
    parsed: ParsedReleaseResponse
    match: AnimeMatchResponse
    ranking: ReleaseRankingResponse


class ReleaseDiscoveryResponse(BaseModel):
    query: str
    queries: list[str]
    warnings: list[str]
    search_profile_version: int | None
    items: list[ReleaseDiscoveryItemResponse]


class ReleaseDiscoveryMatchCandidateResponse(BaseModel):
    anime_id: UUID
    title: str
    matched_titles: list[str]


class ReleaseDiscoveryCandidateResponse(BaseModel):
    id: UUID
    anime_id: UUID
    last_run_id: UUID | None
    provider_source: str
    source_id: str
    source_title: str
    page_url: str
    torrent_url: str
    published_at: datetime | None
    size: str | None
    seeders: int | None
    leechers: int | None
    downloads: int | None
    info_hash: str | None
    normalized_title: str
    release_group: str | None
    series_title: str | None
    episode_number: int | None
    episode_title: str | None
    season_number: int | None
    resolution: str | None
    source: str | None
    video_codec: str | None
    audio_codec: str | None
    bit_depth: int | None
    parse_status: str
    parse_warnings: list[str]
    failed_required_fields: list[str]
    parser_profile_version: int | None
    normalized_series_title: str | None
    match_status: str
    match_candidates: list[ReleaseDiscoveryMatchCandidateResponse]
    ranking_score: int
    ranking_reasons: list[str]
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    reviewed_at: datetime | None
    automation_status: str
    automation_claimed_at: datetime | None
    automation_completed_at: datetime | None
    automation_error: str | None


class ReleaseDiscoveryQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    query: str
    status: str
    result_count: int
    result_cap_reached: bool
    error_message: str | None
    created_at: datetime


class ReleaseDiscoveryRunResponse(BaseModel):
    id: UUID
    anime_id: UUID
    scheduled_for: datetime
    status: str
    query: str | None
    search_profile_version: int | None
    candidate_count: int
    warning_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    queries: list[ReleaseDiscoveryQueryResponse]


class ReleaseDiscoveryScheduleResponse(BaseModel):
    anime_id: UUID
    enabled: bool
    interval_minutes: int
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_run_status: str | None


class ReleaseDiscoveryScheduleUpdate(BaseModel):
    enabled: bool = False
    interval_minutes: int = Field(default=360, ge=15, le=1440)


class ReleaseDiscoveryCandidateUpdate(BaseModel):
    status: str = Field(pattern="^(reviewed|rejected|stale)$")


class AnimeReleasePreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    release_group_id: UUID | None
    resolution: str | None
    video_codec: str | None
    source: str | None
    created_at: datetime | None
    updated_at: datetime | None


class AnimeReleasePreferenceUpdate(BaseModel):
    release_group_id: UUID | None = None
    resolution: str | None = Field(default=None, max_length=32)
    video_codec: str | None = Field(default=None, max_length=32)
    source: str | None = Field(default=None, max_length=32)


class EpisodeCreate(BaseModel):
    episode_number: int = Field(ge=1, le=9999)
    release_group_id: UUID | None = None
    title: str = Field(min_length=1, max_length=300)
    source: str = Field(default="nyaa", min_length=1, max_length=32)
    source_id: str | None = Field(default=None, max_length=256)
    source_title: str | None = Field(default=None, max_length=500)
    source_url: HttpUrl | None = None
    torrent_url: HttpUrl
    size: str | None = Field(default=None, max_length=64)
    seeders: int | None = Field(default=None, ge=0)
    leechers: int | None = Field(default=None, ge=0)
    downloads: int | None = Field(default=None, ge=0)
    info_hash: str | None = Field(default=None, max_length=128)
    download_status: DownloadStatus = DownloadStatus.NOT_STARTED
    conversion_status: ConversionStatus = ConversionStatus.NOT_STARTED


class EpisodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release_group_id: UUID | None = None
    episode_number: int | None = Field(default=None, ge=1, le=9999)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    source: str | None = Field(default=None, min_length=1, max_length=32)
    source_id: str | None = Field(default=None, max_length=256)
    source_title: str | None = Field(default=None, max_length=500)
    source_url: HttpUrl | None = None
    torrent_url: HttpUrl | None = None
    size: str | None = Field(default=None, max_length=64)
    seeders: int | None = Field(default=None, ge=0)
    leechers: int | None = Field(default=None, ge=0)
    downloads: int | None = Field(default=None, ge=0)
    info_hash: str | None = Field(default=None, max_length=128)
    download_status: DownloadStatus | None = None
    conversion_status: ConversionStatus | None = None


class EpisodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    anime_id: UUID
    release_group_id: UUID | None
    episode_number: int
    title: str
    source: str
    source_id: str | None
    source_title: str | None
    source_url: HttpUrl | None
    torrent_url: HttpUrl
    size: str | None
    seeders: int | None
    leechers: int | None
    downloads: int | None
    info_hash: str | None
    download_status: DownloadStatus
    conversion_status: ConversionStatus
    created_at: datetime
    updated_at: datetime


def _empty_episodes() -> list[EpisodeCreate]:
    return []


AnimeTitleKey = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,31}$")]
AnimeTitleValue = Annotated[str, StringConstraints(max_length=200)]


class AnimeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    titles: dict[AnimeTitleKey, AnimeTitleValue] = Field(default_factory=dict)
    year: int = Field(ge=1900, le=2100)
    season: Season
    weekday: Weekday
    air_time: time | None = None
    timezone: str = Field(default="Asia/Tokyo", min_length=1, max_length=64)
    episodes: list[EpisodeCreate] = Field(default_factory=_empty_episodes)


class AnimeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    titles: dict[AnimeTitleKey, AnimeTitleValue] | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    season: Season | None = None
    weekday: Weekday | None = None
    air_time: time | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class AnimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    titles: dict[str, str]
    year: int
    season: Season
    weekday: Weekday
    air_time: time | None
    timezone: str
    created_at: datetime
    updated_at: datetime
    episodes: list[EpisodeResponse]


class DownloadJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    episode_id: UUID
    status: DownloadJobStatus
    downloaded_bytes: int
    total_bytes: int | None
    attempt_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DownloadJobListItemResponse(DownloadJobResponse):
    anime_id: UUID
    anime_title: str
    episode_number: int
    episode_title: str


class DownloadJobListResponse(BaseModel):
    items: list[DownloadJobListItemResponse]
    page: int
    page_size: int
    total: int
    has_more: bool


class SubtitleTrackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_asset_id: UUID
    stream_index: int | None
    language: str | None
    title: str | None
    codec_name: str | None
    source_path: str | None
    normalized_path: str | None
    normalized_format: str | None
    status: SubtitleTrackStatus
    error_message: str | None
    is_default: bool
    is_forced: bool
    created_at: datetime
    updated_at: datetime


class MediaChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_asset_id: UUID
    chapter_index: int
    chapter_id: int | None
    start_time_seconds: float
    end_time_seconds: float
    title: str | None


class MediaFontResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    mime_type: str | None
    sha256: str
    path: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class MediaAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_asset_id: UUID
    attachment_index: int
    stream_index: int
    filename: str | None
    mime_type: str | None
    description: str | None
    is_font: bool
    extracted_path: str | None
    size_bytes: int | None
    font_id: UUID | None
    font: MediaFontResponse | None
    status: MediaAttachmentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    episode_id: UUID
    processing_job_id: UUID | None
    path: str
    format_name: str | None
    duration_seconds: float | None
    size_bytes: int | None
    video_codec: str | None
    audio_codec: str | None
    width: int | None
    height: int | None
    frame_rate: str | None
    metadata_updated_at: datetime | None
    subtitle_tracks_updated_at: datetime | None
    subtitle_tracks_processed_at: datetime | None
    chapters_updated_at: datetime | None
    attachments_updated_at: datetime | None
    attachments_processed_at: datetime | None
    thumbnail_status: MediaThumbnailStatus
    thumbnail_sprite_path: str | None
    thumbnail_vtt_path: str | None
    thumbnail_updated_at: datetime | None
    thumbnail_error_message: str | None
    subtitle_tracks: list[SubtitleTrackResponse]
    chapters: list[MediaChapterResponse]
    attachments: list[MediaAttachmentResponse]
    created_at: datetime
    updated_at: datetime


class PlaybackSourceResponse(BaseModel):
    url: str
    mime_type: str


class PlaybackVideoResponse(BaseModel):
    direct: PlaybackSourceResponse | None
    hls: PlaybackSourceResponse | None
    dash: PlaybackSourceResponse | None


class PlaybackSubtitleResponse(BaseModel):
    id: UUID
    language: str | None
    title: str | None
    is_default: bool
    is_forced: bool
    format: str | None
    url: str


class PlaybackFontResponse(BaseModel):
    id: UUID
    name: str
    mime_type: str | None
    url: str


class PlaybackChapterResponse(BaseModel):
    id: UUID
    title: str | None
    start_time_seconds: float
    end_time_seconds: float


class PlaybackThumbnailResponse(BaseModel):
    sprite_url: str
    vtt_url: str


class PlaybackResponse(BaseModel):
    anime_id: UUID
    episode_id: UUID
    episode_number: int
    title: str
    duration_seconds: float | None
    video: PlaybackVideoResponse | None
    subtitles: list[PlaybackSubtitleResponse]
    fonts: list[PlaybackFontResponse]
    chapters: list[PlaybackChapterResponse]
    thumbnails: PlaybackThumbnailResponse | None



class EpisodePipelineStageStatus(StrEnum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    PROCESSING = "processing"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class EpisodePipelineCurrentStage(StrEnum):
    DOWNLOAD = "download"
    PROCESSING = "processing"
    PREVIEW = "preview"
    STREAMING = "streaming"

class EpisodeMediaSourceStatus(StrEnum):
    NOT_AVAILABLE = "not_available"
    FOUND = MediaSourceStatus.FOUND.value
    MISSING_DIRECTORY = MediaSourceStatus.MISSING_DIRECTORY.value
    NO_MEDIA = MediaSourceStatus.NO_MEDIA.value
    AMBIGUOUS = MediaSourceStatus.AMBIGUOUS.value


class MediaSourceCandidateResponse(BaseModel):
    path: str


class EpisodeMediaSourceResponse(BaseModel):
    episode_id: UUID
    download_job_id: UUID | None
    download_status: DownloadJobStatus | None
    status: EpisodeMediaSourceStatus
    root: str | None
    selected_path: str | None
    candidates: list[MediaSourceCandidateResponse]
    processing_job_id: UUID | None
    processing_status: MediaProcessingJobStatus | None


class MediaSourceSelectionRequest(BaseModel):
    path: str = Field(min_length=1, max_length=2000)


class MediaSourceOrphanResponse(BaseModel):
    directory_id: UUID
    path: str


class EpisodePipelineDownloadResponse(BaseModel):
    job_id: UUID | None
    status: EpisodePipelineStageStatus
    downloaded_bytes: int
    total_bytes: int | None
    error_message: str | None
    updated_at: datetime | None


class EpisodePipelineProcessingResponse(BaseModel):
    job_id: UUID | None
    preparation_job_id: UUID | None
    status: EpisodePipelineStageStatus
    progress_percent: int = Field(ge=0, le=100)
    playable_ready: bool
    error_message: str | None


class EpisodePipelineStreamingResponse(BaseModel):
    job_id: UUID | None
    status: EpisodePipelineStageStatus
    progress_percent: int = Field(ge=0, le=100)
    hls_ready: bool
    dash_ready: bool
    error_message: str | None


class EpisodePipelineThumbnailResponse(BaseModel):
    status: EpisodePipelineStageStatus
    progress_percent: int = Field(ge=0, le=100)
    url: str | None
    vtt_url: str | None
    error_message: str | None


class EpisodePipelineSummary(BaseModel):
    episode_id: UUID
    episode_number: int
    title: str
    download: EpisodePipelineDownloadResponse
    processing: EpisodePipelineProcessingResponse
    subtitles: EpisodePipelineStageStatus
    attachments: EpisodePipelineStageStatus
    streaming: EpisodePipelineStreamingResponse
    thumbnail: EpisodePipelineThumbnailResponse
    current_stage: EpisodePipelineCurrentStage | None
    playback_ready: bool
    active: bool


class AnimePipelineResponse(BaseModel):
    anime_id: UUID
    episodes: list[EpisodePipelineSummary]


class EpisodePipelineRetryResponse(BaseModel):
    stage: EpisodePipelineCurrentStage
    job_id: UUID
    status: EpisodePipelineStageStatus


class MediaProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    episode_id: UUID
    download_job_id: UUID | None
    status: MediaProcessingJobStatus
    media_path: str | None
    probe_metadata: dict[str, object] | None
    attempt_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MediaVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_asset_id: UUID
    kind: MediaVariantKind
    status: MediaVariantStatus
    source_path: str | None
    source_metadata_updated_at: datetime | None
    path: str | None
    format_name: str | None
    duration_seconds: float | None
    size_bytes: int | None
    video_codec: str | None
    audio_codec: str | None
    width: int | None
    height: int | None
    frame_rate: str | None
    error_message: str | None
    current: bool = False
    created_at: datetime
    updated_at: datetime


class MediaPreparationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_asset_id: UUID
    variant_id: UUID
    status: MediaPreparationJobStatus
    operation: MediaTranscodingOperation | None
    source_path: str
    source_metadata_updated_at: datetime
    output_path: str | None
    attempt_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MediaStreamingRepresentationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    package_id: UUID
    quality: str
    width: int
    height: int
    bandwidth: int
    video_codec: str
    audio_codec: str | None
    duration_seconds: float
    hls_playlist_key: str
    init_segment_key: str
    segment_directory_key: str
    status: MediaStreamingRepresentationStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class MediaStreamingPackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_variant_id: UUID
    status: MediaStreamingPackageStatus
    source_path: str
    source_variant_updated_at: datetime
    hls_master_key: str | None
    dash_manifest_key: str | None
    error_message: str | None
    representations: list[MediaStreamingRepresentationResponse]
    created_at: datetime
    updated_at: datetime


class MediaPackagingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_variant_id: UUID
    package_id: UUID
    status: MediaPackagingJobStatus
    source_path: str
    source_variant_updated_at: datetime
    attempt_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EpisodeIngestionStatus(StrEnum):
    CREATED = "created"
    IDEMPOTENT = "idempotent"
    REPLACEMENT_CANDIDATE = "replacement_candidate"
    REPLACED = "replaced"

class EpisodeReleaseReplacementRequest(BaseModel):
    release: ReleaseResponse
    parsed: ParsedReleaseResponse


class EpisodeIngestionRequest(BaseModel):
    anime_id: UUID
    release: ReleaseResponse
    parsed: ParsedReleaseResponse


class EpisodeIngestionResponse(BaseModel):
    status: EpisodeIngestionStatus
    episode: EpisodeResponse | None
    existing_episode: EpisodeResponse | None


class ReleaseAutomationPolicyUpdate(BaseModel):
    enabled: bool = False
    min_ranking_score: int = Field(0, ge=0, le=160)
    require_preference_match: bool = True


class ReleaseAutomationPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    anime_id: UUID
    enabled: bool
    min_ranking_score: int
    require_preference_match: bool
    created_at: datetime | None
    updated_at: datetime | None


class ReleaseAutomationCandidatePreviewResponse(BaseModel):
    candidate: ReleaseDiscoveryCandidateResponse
    eligible: bool
    reasons: list[str]
    automation_status: str


class ReleaseAutomationRunResponse(BaseModel):
    anime_id: UUID
    status: str


class ReleaseDiscoveryCandidateAcceptanceRequest(BaseModel):
    replace_episode_id: UUID | None = None


class ReleaseDiscoveryCandidateAcceptanceResponse(BaseModel):
    status: EpisodeIngestionStatus
    candidate: ReleaseDiscoveryCandidateResponse
    episode: EpisodeResponse | None
    existing_episode: EpisodeResponse | None
