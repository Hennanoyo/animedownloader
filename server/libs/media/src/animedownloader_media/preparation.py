from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import (
    FFmpegProgressCallback,
    FFmpegRunner,
    PlayableMediaProcessingResult,
    build_video_encoder_options,
    run_ffmpeg,
)
from .playback import PlayableMediaOperation
from .thumbnails import ThumbnailSpriteResult, write_thumbnail_webvtt


class FFmpegMediaPreparationProcessingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaPreparationProcessingResult:
    playable: PlayableMediaProcessingResult
    thumbnail: ThumbnailSpriteResult


class FFmpegMediaPreparationProcessor:
    """Prepare playable media and thumbnails with one shared FFmpeg process."""

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
            raise ValueError("Thumbnail dimensions must be positive")
        if columns <= 0 or rows <= 0:
            raise ValueError("Sprite grid dimensions must be positive")
        if max_frames > columns * rows:
            raise ValueError(
                "Thumbnail max_frames cannot exceed sprite capacity: "
                f"{max_frames} > {columns * rows}",
            )

        self._executable = executable
        self._runner = runner or __import__(
            "animedownloader_media.ffmpeg",
            fromlist=["SubprocessFFmpegRunner"],
        ).SubprocessFFmpegRunner()
        self._video_encoder = video_encoder
        build_video_encoder_options(video_encoder)
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
        on_progress: FFmpegProgressCallback | None = None,
    ) -> MediaPreparationProcessingResult:
        if not media_path.is_file():
            raise FFmpegMediaPreparationProcessingError(
                f"Media file does not exist: {media_path}",
            )

        duration = _validated_duration(duration_seconds)
        playable_path.parent.mkdir(parents=True, exist_ok=True)
        sprite_path.parent.mkdir(parents=True, exist_ok=True)
        vtt_path.parent.mkdir(parents=True, exist_ok=True)
        _remove_existing_outputs(playable_path, sprite_path, vtt_path)

        interval = max(
            self._min_interval_seconds,
            duration / self._max_frames,
        )
        frame_count = min(
            self._columns * self._rows,
            max(1, math.ceil(duration / interval)),
        )
        fps = 1 / interval
        thumbnail_filter = (
            f"fps={fps:.12g}:round=up,"
            f"scale={self._width}:{self._height}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={self._width}:{self._height}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,"
            f"tile={self._columns}x{self._rows}:padding=0:margin=0"
        )

        if operation is PlayableMediaOperation.TRANSCODE:
            filter_graph = (
                "[0:v:0]split=2[playable_v][thumbnail_v];"
                f"[thumbnail_v]{thumbnail_filter}[sprite]"
            )
            playable_video_options = build_video_encoder_options(self._video_encoder)
        else:
            filter_graph = f"[0:v:0]{thumbnail_filter}[sprite]"
            playable_video_options = ("-c:v:0", "copy")

        command = (
            self._executable,
            "-v",
            "error",
            "-y",
            "-i",
            str(media_path),
            "-filter_complex",
            filter_graph,
            "-map",
            "[playable_v]" if operation is PlayableMediaOperation.TRANSCODE else "0:v:0",
            "-map",
            "0:a?",
            "-map_chapters",
            "0",
            "-sn",
            "-dn",
            *playable_video_options,
            "-tag:v:0",
            "hvc1",
            "-c:a",
            "copy" if operation is PlayableMediaOperation.REMUX else "aac",
            *(( "-b:a", "192k") if operation is PlayableMediaOperation.TRANSCODE else ()),
            "-movflags",
            "+faststart",
            str(playable_path),
            "-map",
            "[sprite]",
            "-frames:v",
            "1",
            "-c:v",
            "mjpeg",
            "-q:v",
            "5",
            str(sprite_path),
        )

        try:
            result = await run_ffmpeg(
                self._runner,
                command,
                duration_seconds=duration,
                on_progress=on_progress,
            )
            _validate_ffmpeg_result(result, playable_path, "media preparation")
            if not sprite_path.is_file():
                raise FFmpegMediaPreparationProcessingError(
                    "FFmpeg completed without creating thumbnail sprite: "
                    f"{sprite_path}",
                )
            write_thumbnail_webvtt(
                path=vtt_path,
                frame_count=frame_count,
                interval_seconds=interval,
                duration_seconds=duration,
                sprite_filename=sprite_path.name,
                width=self._width,
                height=self._height,
                columns=self._columns,
            )
        except FFmpegMediaPreparationProcessingError:
            raise
        except Exception as exc:
            raise FFmpegMediaPreparationProcessingError(str(exc)) from exc

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
    if (
        duration_seconds is None
        or not math.isfinite(duration_seconds)
        or duration_seconds <= 0
    ):
        raise FFmpegMediaPreparationProcessingError(
            "Combined media preparation requires a positive media duration",
        )
    return duration_seconds


def _remove_existing_outputs(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def _validate_ffmpeg_result(
    result: object,
    output_path: Path,
    operation: str,
) -> None:
    returncode = getattr(result, "returncode", 1)
    if returncode == 0 and output_path.is_file():
        return

    stderr = getattr(result, "stderr", b"")
    message = stderr.decode("utf-8", errors="replace").strip()
    raise FFmpegMediaPreparationProcessingError(
        message
        or f"FFmpeg {operation} failed with exit code {returncode}",
    )

