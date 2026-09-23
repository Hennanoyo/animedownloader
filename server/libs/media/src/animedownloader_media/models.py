from dataclasses import dataclass
from enum import StrEnum


class MediaStreamType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    ATTACHMENT = "attachment"
    DATA = "data"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MediaFormat:
    filename: str | None
    format_name: str | None
    format_long_name: str | None
    start_time_seconds: float | None
    duration_seconds: float | None
    size_bytes: int | None
    bit_rate: int | None
    tags: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class MediaStream:
    index: int
    codec_type: MediaStreamType
    codec_name: str | None
    codec_long_name: str | None
    profile: str | None
    codec_tag_string: str | None
    width: int | None
    height: int | None
    pixel_format: str | None
    frame_rate: str | None
    duration_seconds: float | None
    bit_rate: int | None
    channels: int | None
    channel_layout: str | None
    sample_rate_hz: int | None
    language: str | None
    title: str | None
    disposition_default: bool
    disposition_forced: bool
    tags: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class MediaChapter:
    id: int | None
    start_time_seconds: float
    end_time_seconds: float
    title: str | None


@dataclass(frozen=True, slots=True)
class MediaProbe:
    path: str
    format: MediaFormat
    streams: tuple[MediaStream, ...]
    chapters: tuple[MediaChapter, ...]

    @property
    def video_streams(self) -> tuple[MediaStream, ...]:
        return tuple(stream for stream in self.streams if stream.codec_type is MediaStreamType.VIDEO)

    @property
    def audio_streams(self) -> tuple[MediaStream, ...]:
        return tuple(stream for stream in self.streams if stream.codec_type is MediaStreamType.AUDIO)

    @property
    def subtitle_streams(self) -> tuple[MediaStream, ...]:
        return tuple(
            stream for stream in self.streams if stream.codec_type is MediaStreamType.SUBTITLE
        )

    @property
    def attachment_streams(self) -> tuple[MediaStream, ...]:
        return tuple(
            stream for stream in self.streams if stream.codec_type is MediaStreamType.ATTACHMENT
        )
