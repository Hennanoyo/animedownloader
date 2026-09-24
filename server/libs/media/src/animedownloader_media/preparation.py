from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import (
    FFmpegPlayableMediaProcessor,
    FFmpegRunner,
    PlayableMediaProcessingResult,
    SubprocessFFmpegRunner,
)
from .playback import PlayableMediaOperation
from .thumbnails import FFmpegThumbnailSpriteProcessor, ThumbnailSpriteResult


class FFmpegMediaPreparationProcessingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaPreparationProcessingResult:
    playable: PlayableMediaProcessingResult
    thumbnail: ThumbnailSpriteResult


class FFmpegMediaPreparationProcessor:
    """Prepare playable media and thumbnails with separate FFmpeg processes.

    Keeping the playable transcode and thumbnail extraction in separate
    processes avoids a shared filter graph retaining decoded frames for two
    differently paced outputs. This bounds peak memory usage at the cost of
    decoding the source twice.
    """

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
        self._playable = FFmpegPlayableMediaProcessor(
            executable=executable,
            runner=runner,
            video_encoder=video_encoder,
        )
        self._thumbnail = FFmpegThumbnailSpriteProcessor(
            executable=executable,
            runner=runner,
            min_interval_seconds=min_interval_seconds,
            max_frames=max_frames,
            width=width,
            height=height,
            columns=columns,
            rows=rows,
        )

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

        playable_path.parent.mkdir(parents=True, exist_ok=True)
        sprite_path.parent.mkdir(parents=True, exist_ok=True)
        vtt_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            playable = await self._playable.process(
                media_path=media_path,
                output_path=playable_path,
                operation=operation,
            )
            thumbnail = await self._thumbnail.generate(
                media_path=media_path,
                output_dir=sprite_path.parent,
                duration_seconds=duration_seconds,
            )
        except Exception as exc:
            if isinstance(exc, FFmpegMediaPreparationProcessingError):
                raise
            raise FFmpegMediaPreparationProcessingError(str(exc)) from exc

        if thumbnail.sprite_path != sprite_path or thumbnail.vtt_path != vtt_path:
            raise FFmpegMediaPreparationProcessingError(
                "Thumbnail processor returned unexpected output paths: "
                f"sprite={thumbnail.sprite_path} vtt={thumbnail.vtt_path}",
            )

        return MediaPreparationProcessingResult(
            playable=playable,
            thumbnail=thumbnail,
        )
