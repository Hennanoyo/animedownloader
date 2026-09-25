from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID


class ParseStatus(StrEnum):
    PARSED = "parsed"
    AMBIGUOUS = "ambiguous"
    UNPARSED = "unparsed"
    UNSUPPORTED = "unsupported"


class ParserField(StrEnum):
    RELEASE_GROUP = "release_group"
    SERIES_TITLE = "series_title"
    EPISODE_NUMBER = "episode_number"
    EPISODE_TITLE = "episode_title"
    SEASON_NUMBER = "season_number"
    RESOLUTION = "resolution"
    SOURCE = "source"
    VIDEO_CODEC = "video_codec"
    AUDIO_CODEC = "audio_codec"
    BIT_DEPTH = "bit_depth"


class ParserTransform(StrEnum):
    IDENTITY = "identity"
    STRIP = "strip"
    NORMALIZE_SPACES = "normalize_spaces"
    TO_INT = "to_int"
    LOWER = "lower"
    UPPER = "upper"


SUPPORTED_PARSER_TRANSFORMS: Final[frozenset[ParserTransform]] = frozenset(ParserTransform)


@dataclass(frozen=True, slots=True)
class Release:
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


@dataclass(frozen=True, slots=True)
class ParserRuleSpec:
    field: ParserField
    pattern: str
    priority: int = 100
    required: bool = False
    flags: str = ""
    transform: ParserTransform = ParserTransform.IDENTITY


@dataclass(frozen=True, slots=True)
class ParserProfileSpec:
    release_group: str
    version: int
    rules: tuple[ParserRuleSpec, ...]


@dataclass(frozen=True, slots=True)
class ParsedRelease:
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
    status: ParseStatus
    warnings: tuple[str, ...] = ()
    failed_required_fields: tuple[ParserField, ...] = ()
    parser_profile_version: int | None = None

    @property
    def is_actionable(self) -> bool:
        return (
            self.status == ParseStatus.PARSED
            and self.series_title is not None
            and self.episode_number is not None
        )




class AnimeMatchStatus(StrEnum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    UNMATCHED = "unmatched"


@dataclass(frozen=True, slots=True)
class AnimeMatchCandidate:
    anime_id: UUID
    title: str
    matched_titles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AnimeMatchResult:
    status: AnimeMatchStatus
    normalized_series_title: str | None
    candidates: tuple[AnimeMatchCandidate, ...] = ()


class SearchField(StrEnum):
    GROUP = "group"
    TITLE = "title"
    EPISODE = "episode"
    RESOLUTION = "resolution"
    CODEC = "codec"


@dataclass(frozen=True, slots=True)
class SearchQueryContext:
    group: str | None = None
    title: str | None = None
    episode: int | None = None
    resolution: str | None = None
    codec: str | None = None


@dataclass(frozen=True, slots=True)
class SearchProfileSpec:
    release_group: str
    version: int
    fields: tuple[SearchField, ...]
