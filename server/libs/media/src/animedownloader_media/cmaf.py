from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import FFmpegCommandResult, FFmpegRunner, SubprocessFFmpegRunner


class CMAFPackagingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CMAFMediaSegment:
    number: int
    duration_seconds: float
    uri: str


@dataclass(frozen=True, slots=True)
class CMAFMediaPlaylist:
    target_duration_seconds: int
    init_uri: str
    segments: tuple[CMAFMediaSegment, ...]


@dataclass(frozen=True, slots=True)
class CMAFPackagingResult:
    playlist_path: Path
    init_segment_path: Path
    segments: tuple[CMAFMediaSegment, ...]


@dataclass(frozen=True, slots=True)
class CMAFRepresentationMetadata:
    quality: str
    width: int
    height: int
    bandwidth: int
    video_codec: str
    audio_codec: str | None
    duration_seconds: float
    init_uri: str
    segment_template: str
    segments: tuple[CMAFMediaSegment, ...]


class FFmpegCMAFProcessor:
    def __init__(
        self,
        *,
        executable: str = "ffmpeg",
        runner: FFmpegRunner | None = None,
        segment_duration_seconds: float = 4.0,
    ) -> None:
        if segment_duration_seconds <= 0:
            raise ValueError("segment_duration_seconds must be positive")
        self._executable = executable
        self._runner = runner or SubprocessFFmpegRunner()
        self._segment_duration_seconds = segment_duration_seconds

    async def process(
        self,
        *,
        media_path: Path,
        output_dir: Path,
    ) -> CMAFPackagingResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "s").mkdir(parents=True, exist_ok=True)

        playlist_path = output_dir / "index.m3u8"

        result = await self._runner.run(
            (
                self._executable,
                "-v",
                "error",
                "-y",
                "-i",
                str(media_path),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-sn",
                "-dn",
                "-c",
                "copy",
                "-f",
                "hls",
                "-hls_segment_type",
                "fmp4",
                "-hls_time",
                f"{self._segment_duration_seconds:g}",
                "-hls_playlist_type",
                "vod",
                "-hls_fmp4_init_filename",
                "init.mp4",
                "-hls_segment_filename",
                "s/%05d.m4s",
                "-start_number",
                "0",
                str(playlist_path),
            ),
        )
        _validate_ffmpeg_result(result, playlist_path)

        raw_playlist = playlist_path.read_text(encoding="utf-8")
        playlist = parse_cmaf_media_playlist(raw_playlist)
        normalized_playlist, normalized_segments = _normalize_segment_uris(
            playlist_path=playlist_path,
            content=raw_playlist,
            segments=playlist.segments,
        )
        if normalized_playlist != raw_playlist:
            playlist_path.write_text(normalized_playlist, encoding="utf-8")
        init_segment_path = _resolve_playlist_path(playlist_path, playlist.init_uri)
        if not init_segment_path.is_file():
            raise CMAFPackagingError(
                "FFmpeg completed without creating CMAF init segment: "
                f"{init_segment_path}",
            )

        for segment in playlist.segments:
            segment_path = _resolve_playlist_path(playlist_path, segment.uri)
            if not segment_path.is_file():
                raise CMAFPackagingError(
                    "FFmpeg completed without creating CMAF segment: "
                    f"{segment_path}",
                )

        return CMAFPackagingResult(
            playlist_path=playlist_path,
            init_segment_path=init_segment_path,
            segments=normalized_segments,
        )


def parse_cmaf_media_playlist(content: str) -> CMAFMediaPlaylist:
    target_duration: int | None = None
    init_uri: str | None = None
    segments: list[CMAFMediaSegment] = []
    pending_duration: float | None = None
    media_sequence = 0

    for line in (item.strip() for item in content.splitlines()):
        if not line:
            continue
        if line.startswith("#EXT-X-TARGETDURATION:"):
            target_duration = int(line.partition(":")[2])
        elif line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            media_sequence = int(line.partition(":")[2])
        elif line.startswith("#EXT-X-MAP:"):
            match = re.search(r'URI="([^"]+)"', line)
            if match is None:
                raise CMAFPackagingError("HLS media playlist has an invalid EXT-X-MAP")
            init_uri = match.group(1)
        elif line.startswith("#EXTINF:"):
            pending_duration = float(line.partition(":")[2].rstrip(","))
        elif not line.startswith("#"):
            if pending_duration is None:
                raise CMAFPackagingError(
                    "HLS media playlist contains a segment without EXTINF",
                )
            segments.append(
                CMAFMediaSegment(
                    number=media_sequence + len(segments),
                    duration_seconds=pending_duration,
                    uri=line,
                ),
            )
            pending_duration = None

    if target_duration is None:
        raise CMAFPackagingError("HLS media playlist is missing target duration")
    if init_uri is None:
        raise CMAFPackagingError("HLS media playlist is missing initialization segment")
    if not segments:
        raise CMAFPackagingError("HLS media playlist contains no media segments")

    return CMAFMediaPlaylist(
        target_duration_seconds=target_duration,
        init_uri=init_uri,
        segments=tuple(segments),
    )


def _normalize_segment_uris(
    *,
    playlist_path: Path,
    content: str,
    segments: Sequence[CMAFMediaSegment],
) -> tuple[str, tuple[CMAFMediaSegment, ...]]:
    segment_by_uri = {segment.uri: segment for segment in segments}
    normalized_segments = tuple(
        CMAFMediaSegment(
            number=segment.number,
            duration_seconds=segment.duration_seconds,
            uri=f"s/{Path(segment.uri).name}",
        )
        for segment in segments
    )

    normalized_content: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        segment = segment_by_uri.get(stripped)
        if segment is None:
            normalized_content.append(line)
            continue
        normalized_content.append(
            f"s/{Path(segment.uri).name}",
        )

    return "\n".join(normalized_content) + "\n", normalized_segments


def build_hls_master_playlist(
    representations: Sequence[CMAFRepresentationMetadata],
) -> str:
    if not representations:
        raise ValueError("At least one CMAF representation is required")

    lines = ["#EXTM3U", "#EXT-X-VERSION:7"]
    for representation in representations:
        codecs = _codec_string(
            representation.video_codec,
            representation.audio_codec,
        )
        lines.extend(
            [
                (
                    "#EXT-X-STREAM-INF:"
                    f"BANDWIDTH={representation.bandwidth},"
                    f"RESOLUTION={representation.width}x{representation.height},"
                    f'CODECS="{codecs}"'
                ),
                f"{representation.quality}/index.m3u8",
            ],
        )
    return "\n".join(lines) + "\n"


def build_dash_manifest(
    representations: Sequence[CMAFRepresentationMetadata],
    *,
    media_presentation_duration_seconds: float,
) -> str:
    if not representations:
        raise ValueError("At least one CMAF representation is required")

    max_segment_duration = max(
        segment.duration_seconds
        for representation in representations
        for segment in representation.segments
    )
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" '
            'profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" '
            'type="static" '
            f'mediaPresentationDuration="{_format_duration(media_presentation_duration_seconds)}" '
            f'minBufferTime="{_format_duration(min(2.0, max_segment_duration))}">'
        ),
        '  <Period id="0" start="PT0S">',
        '    <AdaptationSet id="0" contentType="video" segmentAlignment="true">',
    ]

    for representation in representations:
        codecs = _codec_string(
            representation.video_codec,
            representation.audio_codec,
        )
        lines.extend(
            [
                (
                    f'      <Representation id="{representation.quality}" '
                    'mimeType="video/mp4" '
                    f'codecs="{codecs}" '
                    f'bandwidth="{representation.bandwidth}" '
                    f'width="{representation.width}" '
                    f'height="{representation.height}">'
                ),
                (
                    '        <SegmentTemplate timescale="1000" '
                    f'initialization="{representation.init_uri}" '
                    f'media="{representation.segment_template}" '
                    'startNumber="0">'
                ),
                "          <SegmentTimeline>",
            ],
        )

        timestamp_ms = 0
        for segment in representation.segments:
            duration_ms = max(1, round(segment.duration_seconds * 1000))
            lines.append(
                f'            <S t="{timestamp_ms}" d="{duration_ms}" />',
            )
            timestamp_ms += duration_ms

        lines.extend(
            [
                "          </SegmentTimeline>",
                "        </SegmentTemplate>",
                "      </Representation>",
            ],
        )

    lines.extend(
        [
            "    </AdaptationSet>",
            "  </Period>",
            "</MPD>",
        ],
    )
    return "\n".join(lines) + "\n"


def make_representation_metadata(
    *,
    quality: str,
    width: int | None,
    height: int | None,
    size_bytes: int | None,
    duration_seconds: float | None,
    video_codec: str | None,
    audio_codec: str | None,
    segments: Sequence[CMAFMediaSegment],
) -> CMAFRepresentationMetadata:
    if width is None or height is None:
        raise CMAFPackagingError(
            "CMAF representation requires known video dimensions",
        )
    if duration_seconds is None or duration_seconds <= 0:
        raise CMAFPackagingError(
            "CMAF representation requires a positive duration",
        )
    if video_codec is None:
        raise CMAFPackagingError(
            "CMAF representation requires a video codec",
        )
    if not segments:
        raise CMAFPackagingError("CMAF representation requires media segments")

    estimated_bandwidth = int((size_bytes or 0) * 8 / duration_seconds)
    return CMAFRepresentationMetadata(
        quality=quality,
        width=width,
        height=height,
        bandwidth=max(1, estimated_bandwidth),
        video_codec=video_codec,
        audio_codec=audio_codec,
        duration_seconds=duration_seconds,
        init_uri=f"{quality}/init.mp4",
        segment_template=f"{quality}/s/$Number%05d$.m4s",
        segments=tuple(segments),
    )


def _codec_string(video_codec: str, audio_codec: str | None) -> str:
    video = "hvc1" if video_codec.casefold() == "hevc" else video_codec
    codecs = [video]
    if audio_codec is not None:
        codecs.append(
            "mp4a.40.2" if audio_codec.casefold() == "aac" else audio_codec,
        )
    return ",".join(codecs)


def _format_duration(seconds: float) -> str:
    return f"PT{seconds:.3f}S"


def _resolve_playlist_path(playlist_path: Path, uri: str) -> Path:
    path = Path(uri)
    if path.is_absolute() or ".." in path.parts:
        raise CMAFPackagingError(f"Invalid playlist resource path: {uri}")
    return playlist_path.parent / path


def _validate_ffmpeg_result(
    result: FFmpegCommandResult,
    playlist_path: Path,
) -> None:
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise CMAFPackagingError(
            message
            or f"FFmpeg CMAF packaging failed with exit code {result.returncode}",
        )
    if not playlist_path.is_file():
        raise CMAFPackagingError(
            "FFmpeg completed without creating HLS media playlist: "
            f"{playlist_path}",
        )
