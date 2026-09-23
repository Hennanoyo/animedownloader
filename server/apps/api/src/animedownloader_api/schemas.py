from datetime import datetime, time
from uuid import UUID

from animedownloader_anime import ConversionStatus, DownloadStatus, Season, Weekday
from animedownloader_download import DownloadJobStatus
from animedownloader_media_processing import MediaProcessingJobStatus
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
    created_at: datetime
    updated_at: datetime


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
