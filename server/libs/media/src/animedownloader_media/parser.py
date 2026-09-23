from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import MediaProbeError
from .models import MediaChapter, MediaFormat, MediaProbe, MediaStream, MediaStreamType


def parse_ffprobe_json(payload: str | bytes, source: Path) -> MediaProbe:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise MediaProbeError(f"Invalid FFprobe JSON for {source}: {exc.msg}") from exc

    if not isinstance(data, Mapping):
        raise MediaProbeError(f"FFprobe output must be a JSON object for {source}")

    raw_format = data.get("format")
    if not isinstance(raw_format, Mapping):
        raise MediaProbeError(f"FFprobe output does not contain a valid format object for {source}")

    raw_streams = data.get("streams", [])
    raw_chapters = data.get("chapters", [])

    if not isinstance(raw_streams, list) or not isinstance(raw_chapters, list):
        raise MediaProbeError(f"FFprobe streams and chapters must be arrays for {source}")

    return MediaProbe(
        path=str(source),
        format=_parse_format(raw_format),
        streams=tuple(
            _parse_stream(item, source, position)
            for position, item in enumerate(raw_streams)
            if isinstance(item, Mapping)
        ),
        chapters=tuple(
            _parse_chapter(item, source, position)
            for position, item in enumerate(raw_chapters)
            if isinstance(item, Mapping)
        ),
    )


def _parse_format(data: Mapping[str, Any]) -> MediaFormat:
    return MediaFormat(
        filename=_string(data.get("filename")),
        format_name=_string(data.get("format_name")),
        format_long_name=_string(data.get("format_long_name")),
        start_time_seconds=_float(data.get("start_time")),
        duration_seconds=_float(data.get("duration")),
        size_bytes=_int(data.get("size")),
        bit_rate=_int(data.get("bit_rate")),
        tags=_parse_tags(data.get("tags")),
    )


def _parse_stream(
    data: Mapping[str, Any],
    source: Path,
    position: int,
) -> MediaStream:
    stream_index = _int(data.get("index"))
    if stream_index is None:
        stream_index = position

    disposition = data.get("disposition")
    if not isinstance(disposition, Mapping):
        disposition = {}

    tags = _parse_tags(data.get("tags"))

    return MediaStream(
        index=stream_index,
        codec_type=_stream_type(data.get("codec_type")),
        codec_name=_string(data.get("codec_name")),
        codec_long_name=_string(data.get("codec_long_name")),
        profile=_string(data.get("profile")),
        codec_tag_string=_string(data.get("codec_tag_string")),
        width=_int(data.get("width")),
        height=_int(data.get("height")),
        pixel_format=_string(data.get("pix_fmt")),
        frame_rate=_string(data.get("r_frame_rate")),
        duration_seconds=_float(data.get("duration")),
        bit_rate=_int(data.get("bit_rate")),
        channels=_int(data.get("channels")),
        channel_layout=_string(data.get("channel_layout")),
        sample_rate_hz=_int(data.get("sample_rate")),
        language=_tag_value(tags, "language"),
        title=_tag_value(tags, "title"),
        disposition_default=bool(disposition.get("default", 0)),
        disposition_forced=bool(disposition.get("forced", 0)),
        tags=tags,
    )


def _parse_chapter(
    data: Mapping[str, Any],
    source: Path,
    position: int,
) -> MediaChapter:
    start_time = _float(data.get("start_time"))
    end_time = _float(data.get("end_time"))
    if start_time is None or end_time is None:
        raise MediaProbeError(
            f"Chapter {position} in FFprobe output is missing timing information for {source}"
        )

    tags = data.get("tags")
    if not isinstance(tags, Mapping):
        tags = {}

    return MediaChapter(
        id=_int(data.get("id")),
        start_time_seconds=start_time,
        end_time_seconds=end_time,
        title=_string(tags.get("title")),
    )


def _stream_type(value: Any) -> MediaStreamType:
    raw = _string(value)
    if raw is None:
        return MediaStreamType.UNKNOWN
    try:
        return MediaStreamType(raw)
    except ValueError:
        return MediaStreamType.UNKNOWN


def _parse_tags(value: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, Mapping):
        return ()

    items = []
    for key, raw_value in value.items():
        value = _string(raw_value)
        if value is not None:
            items.append((str(key), value))
    return tuple(items)


def _tag_value(tags: tuple[tuple[str, str], ...], key: str) -> str | None:
    for tag_key, value in tags:
        if tag_key.casefold() == key:
            return value
    return None


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
