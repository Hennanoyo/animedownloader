from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import (
    FFmpegCommandResult,
    FFmpegRunner,
    PlayableMediaProcessingResult,
    SubprocessFFmpegRunner,
    build_video_encoder_options,
)
from .playback import PlayableMediaOperation
from .thumbnails import ThumbnailSpriteResult


class FFmpegMediaPreparationProcessingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaPreparationProcessingResult:
    playable: PlayableMediaProcessingResult
    thumbnail: ThumbnailSpriteResult


class FFmpegMediaPreparationProcessor:
    def __init__(
        self,
        *,
        executable: str = "ffmpeg",
        runner: FFmpegRunner | None = None,
        video_encoder: str = "libx265",
        min_interval_seconds: float = 5.0,
        max_frames: int = 180,
        width: int = 160,
        height: int = 90,
        columns: int = 15,
        rows: int = 12,
    ) -> None:
        if min_interval_seconds <= 0:
            raise ValueError("min_interval_seconds must be positive")
        if max_frames <= 0:
            raise ValueError("max_frames must be positive")
        if width <= 0 or height <= 0:
            raise ValueError("Media preparation dimensions must be positive")
        if columns <= 0 or rows <= 0:
            raise ValueError("Media preparation grid dimensions must be positive")

        capacity = columns * rows
        if max_frames > capacity:
            raise ValueError(
                "Media preparation max_frames cannot exceed sprite capacity: "
                f"{max_frames} > {capacity}",
            )

        self._executable = executable
        self._runner = runner or SubprocessFFmpegRunner()
        self._video_encoder = video_encoder
        self._min_interval_seconds = min_interval_seconds
        self._max_frames = max_frames
        self._width = width
        self._height = height
        self._columns = columns
        self._rows = rows

    async def process(
        self,
        *,
        media_path: Path,
        playable_path: Path,
        sprite_path: Path,
        vtt_path: Path,
        duration_seconds: float | None,
        operation: PlayableMediaOperation,
    ) -> MediaPreparationProcessingResult:
        if not media_path.is_file():
            raise FFmpegMediaPreparationProcessingError(
                f"Media file does not exist: {media_path}",
            )

        duration = _validated_duration(duration_seconds)
        interval = max(
            self._min_interval_seconds,
            duration / self._max_frames,
        )
        frame_count = max(1, math.ceil(duration / interval))

        playable_path.parent.mkdir(parents=True, exist_ok=True)
        sprite_path.parent.mkdir(parents=True, exist_ok=True)
        if playable_path.exists():
            playable_path.unlink()
        if sprite_path.exists():
            sprite_path.unlink()
        if vtt_path.exists():
            vtt_path.unlink()

        thumbnail_filter = (
            f"fps={1 / interval:.12g}:round=up,"
            f"scale={self._width}:{self._height}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={self._width}:{self._height}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,"
            f"tile={self._columns}x{self._rows}:padding=0:margin=0"
        )

        if operation is PlayableMediaOperation.TRANSCODE:
            filter_complex = (
                "[0:v:0]split=2[playable][thumbnail];"
                f"[thumbnail]{thumbnail_filter}[sprite]"
            )
            playable_video_map = "[playable]"
            video_options = build_video_encoder_options(self._video_encoder)
            audio_codec = "aac"
            audio_options = ("-b:a", "192k")
        else:
            filter_complex = (
                f"[0:v:0]{thumbnail_filter}[sprite]"
            )
            playable_video_map = "0:v:0"
            video_options = ("-c:v", "copy")
            audio_codec = "copy"
            audio_options = ()

        result = await self._runner.run(
            (
                self._executable,
                "-v",
                "error",
                "-y",
                "-i",
                str(media_path),
                "-filter_complex_threads",
                "2",
                "-filter_complex",
                filter_complex,
                "-map",
                playable_video_map,
                "-map",
                "0:a?",
                "-map_chapters",
                "0",
                "-sn",
                "-dn",
                *video_options,
                "-tag:v",
                "hvc1",
                "-c:a",
                audio_codec,
                *audio_options,
                "-movflags",
                "+faststart",
                str(playable_path),
                "-map",
                "[sprite]",
                "-frames:v",
                "1",
                "-q:v",
                "5",
                str(sprite_path),
            ),
        )
        _validate_result(result, playable_path, sprite_path)

        if not sprite_path.is_file():
            raise FFmpegMediaPreparationProcessingError(
                f"FFmpeg completed without creating thumbnail sprite: {sprite_path}",
            )

        _write_webvtt(
            path=vtt_path,
            frame_count=frame_count,
            interval_seconds=interval,
            duration_seconds=duration,
            sprite_filename=sprite_path.name,
            width=self._width,
            height=self._height,
            columns=self._columns,
        )

        return MediaPreparationProcessingResult(
            playable=PlayableMediaProcessingResult(
                output_path=playable_path,
                operation=operation,
            ),
            thumbnail=ThumbnailSpriteResult(
                sprite_path=sprite_path,
                vtt_path=vtt_path,
                frame_count=frame_count,
                interval_seconds=interval,
            ),
        )


def _validated_duration(duration_seconds: float | None) -> float:
    if duration_seconds is None or not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise FFmpegMediaPreparationProcessingError(
            "Media preparation requires a positive media duration",
        )
    return duration_seconds


def _validate_result(
    result: FFmpegCommandResult,
    playable_path: Path,
    sprite_path: Path,
) -> None:
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise FFmpegMediaPreparationProcessingError(
            message
            or "FFmpeg media preparation failed with exit code "
            f"{result.returncode}",
        )
    if not playable_path.is_file():
        raise FFmpegMediaPreparationProcessingError(
            f"FFmpeg completed without creating playable output: {playable_path}",
        )
    if not sprite_path.is_file():
        raise FFmpegMediaPreparationProcessingError(
            f"FFmpeg completed without creating thumbnail sprite: {sprite_path}",
        )


def _write_webvtt(
    *,
    path: Path,
    frame_count: int,
    interval_seconds: float,
    duration_seconds: float,
    sprite_filename: str,
    width: int,
    height: int,
    columns: int,
) -> None:
    lines = ["WEBVTT", ""]
    for index in range(frame_count):
        start = index * interval_seconds
        end = min(start + interval_seconds, duration_seconds)
        if end <= start:
            end = start + interval_seconds

        column = index % columns
        row = index // columns
        x = column * width
        y = row * height

        lines.extend(
            (
                f"{_format_timestamp(start)} --> {_format_timestamp(end)}",
                f"{sprite_filename}#xywh={x},{y},{width},{height}",
                "",
            ),
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"
