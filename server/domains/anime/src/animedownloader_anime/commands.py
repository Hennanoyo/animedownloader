from dataclasses import dataclass
from datetime import time

from .enums import ConversionStatus, DownloadStatus, Season, Weekday


@dataclass(frozen=True, slots=True)
class EpisodeCreateData:
    episode_number: int
    title: str
    source: str
    source_id: str | None
    source_title: str | None
    source_url: str | None
    torrent_url: str
    size: str | None
    seeders: int | None
    leechers: int | None
    downloads: int | None
    info_hash: str | None
    download_status: DownloadStatus = DownloadStatus.NOT_STARTED
    conversion_status: ConversionStatus = ConversionStatus.NOT_STARTED


@dataclass(frozen=True, slots=True)
class EpisodeUpdateData:
    episode_number: int | None = None
    title: str | None = None
    source: str | None = None
    source_id: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    torrent_url: str | None = None
    size: str | None = None
    seeders: int | None = None
    leechers: int | None = None
    downloads: int | None = None
    info_hash: str | None = None
    download_status: DownloadStatus | None = None
    conversion_status: ConversionStatus | None = None


@dataclass(frozen=True, slots=True)
class AnimeCreateData:
    title: str
    titles: dict[str, str]
    year: int
    season: Season
    weekday: Weekday
    air_time: time | None
    timezone: str
    episodes: tuple[EpisodeCreateData, ...]


@dataclass(frozen=True, slots=True)
class AnimeUpdateData:
    title: str | None = None
    titles: dict[str, str] | None = None
    year: int | None = None
    season: Season | None = None
    weekday: Weekday | None = None
    air_time: time | None = None
    timezone: str | None = None
