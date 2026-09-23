from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import FFmpegCommandResult, FFmpegRunner, SubprocessFFmpegRunner


class FFmpegThumbnailProcessingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ThumbnailSpriteResult:
    sprite_path: Path
    vtt_path: Path
    frame_count: int
    interval_seconds: float


class FFmpegThumbnailSpriteProcessor:
    def __init__(
        self,
        *,
        executable: str = "ffmpeg",
        runner: FFmpegRunner | None = None,
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
            raise ValueError("Thumbnail dimensions must be positive")
        if columns <= 0 or rows <= 0:
            raise ValueError("Sprite grid dimensions must be positive")

        self._executable = executable
        self._runner = runner or SubprocessFFmpegRunner()
        self._min_interval_seconds = min_interval_seconds
        self._max_frames = max_frames
        self._width = width
        self._height = height
        self._columns = columns
        self._rows = rows

    async def generate(
        self,
        *,
        media_path: Path,
        output_dir: Path,
        duration_seconds: float | None,
    ) -> ThumbnailSpriteResult:
        if not media_path.is_file():
            raise FFmpegThumbnailProcessingError(
                f"Media file does not exist: {media_path}",
            )

        duration = _validated_duration(duration_seconds)
        capacity = self._columns * self._rows
        if self._max_frames > capacity:
            raise FFmpegThumbnailProcessingError(
                "Thumbnail max_frames cannot exceed sprite capacity: "
                f"{self._max_frames} > {capacity}",
            )

        interval = max(self._min_interval_seconds, duration / self._max_frames)

        output_dir.mkdir(parents=True, exist_ok=True)
        sprite_path = output_dir / "sprite.jpg"
        vtt_path = output_dir / "sprite.vtt"
        _remove_existing_outputs(sprite_path, vtt_path)

        with tempfile.TemporaryDirectory(
            dir=output_dir,
            prefix=".frames-",
        ) as temporary_dir:
            frame_dir = Path(temporary_dir)
            frame_pattern = frame_dir / "frame-%05d.jpg"
            scale_filter = (
                f"fps={1 / interval:.12g}:round=up,"
                f"scale={self._width}:{self._height}:force_original_aspect_ratio=decrease,"
                f"pad={self._width}:{self._height}:(ow-iw)/2:(oh-ih)/2,"
                "setsar=1"
            )
            extraction_result = await self._runner.run(
                (
                    self._executable,
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(media_path),
                    "-vf",
                    scale_filter,
                    "-q:v",
                    "5",
                    str(frame_pattern),
                ),
            )
            _validate_ffmpeg_result(
                extraction_result,
                "thumbnail frame extraction",
            )

            frame_paths = sorted(frame_dir.glob("frame-*.jpg"))
            if not frame_paths:
                raise FFmpegThumbnailProcessingError(
                    f"FFmpeg completed without creating thumbnail frames: {media_path}",
                )

            if len(frame_paths) > capacity:
                raise FFmpegThumbnailProcessingError(
                    "Thumbnail frame count exceeds sprite capacity: "
                    f"{len(frame_paths)} > {capacity}",
                )

            sprite_result = await self._runner.run(
                (
                    self._executable,
                    "-v",
                    "error",
                    "-y",
                    "-framerate",
                    "1",
                    "-i",
                    str(frame_pattern),
                    "-vf",
                    f"tile={self._columns}x{self._rows}:padding=0:margin=0",
                    "-frames:v",
                    "1",
                    "-q:v",
                    "5",
                    str(sprite_path),
                ),
            )
            _validate_ffmpeg_result(
                sprite_result,
                "thumbnail sprite generation",
            )

        if not sprite_path.is_file():
            raise FFmpegThumbnailProcessingError(
                f"FFmpeg completed without creating thumbnail sprite: {sprite_path}",
            )

        _write_webvtt(
            path=vtt_path,
            frame_count=len(frame_paths),
            interval_seconds=interval,
            duration_seconds=duration,
            sprite_filename=sprite_path.name,
            width=self._width,
            height=self._height,
            columns=self._columns,
        )

        return ThumbnailSpriteResult(
            sprite_path=sprite_path,
            vtt_path=vtt_path,
            frame_count=len(frame_paths),
            interval_seconds=interval,
        )


def _validated_duration(duration_seconds: float | None) -> float:
    if duration_seconds is None or not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise FFmpegThumbnailProcessingError(
            "Thumbnail generation requires a positive media duration",
        )
    return duration_seconds


def _remove_existing_outputs(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def _validate_ffmpeg_result(
    result: FFmpegCommandResult,
    operation: str,
) -> None:
    if result.returncode == 0:
        return

    message = result.stderr.decode("utf-8", errors="replace").strip()
    raise FFmpegThumbnailProcessingError(
        message or f"FFmpeg {operation} failed with exit code {result.returncode}",
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
