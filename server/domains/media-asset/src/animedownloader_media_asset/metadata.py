from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MediaAssetMetadata:
    format_name: str | None
    duration_seconds: float | None
    size_bytes: int | None
    video_codec: str | None
    audio_codec: str | None
    width: int | None
    height: int | None
    frame_rate: str | None


@dataclass(frozen=True, slots=True)
class SubtitleTrackMetadata:
    stream_index: int | None
    language: str | None
    title: str | None
    codec_name: str | None
    source_path: str | None
    is_default: bool
    is_forced: bool
