from datetime import datetime, time
from enum import StrEnum
from uuid import UUID

from animedownloader_anime import ConversionStatus, DownloadStatus, Season, Weekday
from animedownloader_download import DownloadJobStatus
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
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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


class EpisodeCreate(BaseModel):
    episode_number: int = Field(ge=1, le=9999)
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


class AnimeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    year: int = Field(ge=1900, le=2100)
    season: Season
    weekday: Weekday
    air_time: time | None = None
    timezone: str = Field(default="Asia/Tokyo", min_length=1, max_length=64)
    episodes: list[EpisodeCreate] = Field(default_factory=_empty_episodes)


class AnimeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    year: int | None = Field(default=None, ge=1900, le=2100)
    season: Season | None = None
    weekday: Weekday | None = None
    air_time: time | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class AnimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
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


class EpisodePipelineDownloadResponse(BaseModel):
    status: EpisodePipelineStageStatus
    downloaded_bytes: int
    total_bytes: int | None
    error_message: str | None


class EpisodePipelineProcessingResponse(BaseModel):
    status: EpisodePipelineStageStatus
    progress_percent: int = Field(ge=0, le=100)
    playable_ready: bool
    error_message: str | None


class EpisodePipelineStreamingResponse(BaseModel):
    status: EpisodePipelineStageStatus
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
