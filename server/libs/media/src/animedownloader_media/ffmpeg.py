from __future__ import annotations

import asyncio
import logging
import shlex
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .playback import PlayableMediaOperation


logger = logging.getLogger(__name__)

DEFAULT_FFMPEG_TIMEOUT_SECONDS = 1800.0
DEFAULT_FFMPEG_HEARTBEAT_INTERVAL_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class FFmpegCommandResult:
    stdout: bytes
    stderr: bytes
    returncode: int


class FFmpegRunner(Protocol):
    async def run(self, args: Sequence[str]) -> FFmpegCommandResult: ...


class FFmpegTimeoutError(RuntimeError):
    pass


class SubprocessFFmpegRunner:
    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_FFMPEG_TIMEOUT_SECONDS,
        heartbeat_interval_seconds: float = DEFAULT_FFMPEG_HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive")

        self._timeout_seconds = timeout_seconds
        self._heartbeat_interval_seconds = heartbeat_interval_seconds

    async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
        command = tuple(args)
        started_at = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info(
            "FFmpeg started: pid=%s command=%s",
            process.pid,
            shlex.join(command),
        )

        communication = asyncio.create_task(process.communicate())
        try:
            while True:
                elapsed = time.monotonic() - started_at
                remaining = self._timeout_seconds - elapsed
                if remaining <= 0:
                    raise TimeoutError

                try:
                    stdout, stderr = await asyncio.wait_for(
                        asyncio.shield(communication),
                        timeout=min(self._heartbeat_interval_seconds, remaining),
                    )
                    break
                except asyncio.TimeoutError:
                    elapsed = time.monotonic() - started_at
                    logger.info(
                        "FFmpeg still running: pid=%s elapsed=%.0fs",
                        process.pid,
                        elapsed,
                    )

            elapsed = time.monotonic() - started_at
            returncode = process.returncode or 0
            logger.info(
                "FFmpeg finished: pid=%s elapsed=%.1fs returncode=%s",
                process.pid,
                elapsed,
                returncode,
            )
            return FFmpegCommandResult(
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
            )
        except TimeoutError as exc:
            process.kill()
            await communication
            elapsed = time.monotonic() - started_at
            logger.error(
                "FFmpeg timed out: pid=%s elapsed=%.1fs timeout=%.1fs command=%s",
                process.pid,
                elapsed,
                self._timeout_seconds,
                shlex.join(command),
            )
            raise FFmpegTimeoutError(
                "FFmpeg timed out after "
                f"{self._timeout_seconds:.1f}s: {shlex.join(command)}",
            ) from exc
        except asyncio.CancelledError:
            process.kill()
            await communication
            logger.warning("FFmpeg cancelled: pid=%s", process.pid)
            raise


class SubtitleProcessingError(RuntimeError):
    pass


class UnsupportedSubtitleCodecError(SubtitleProcessingError):
    pass


_TEXT_SUBTITLE_CODECS = frozenset(
    {
        "ass",
        "ssa",
        "subrip",
        "text",
        "webvtt",
        "mov_text",
    }
)


class FFmpegSubtitleProcessor:
    def __init__(
        self,
        *,
        executable: str = "ffmpeg",
        runner: FFmpegRunner | None = None,
    ) -> None:
        self._executable = executable
        self._runner = runner or SubprocessFFmpegRunner()

    async def extract(
        self,
        *,
        media_path: Path,
        stream_index: int,
        codec_name: str | None,
        output_path: Path,
    ) -> str:
        codec = codec_name.casefold() if codec_name is not None else ""
        if codec not in _TEXT_SUBTITLE_CODECS:
            raise UnsupportedSubtitleCodecError(
                "Subtitle codec is not supported for ASS normalization: "
                f"{codec_name or 'unknown'}",
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        encoder = "copy" if codec in {"ass", "ssa"} else "ass"

        result = await self._runner.run(
            (
                self._executable,
                "-v",
                "error",
                "-y",
                "-i",
                str(media_path),
                "-map",
                f"0:{stream_index}",
                "-c:s",
                encoder,
                str(output_path),
            ),
        )
        _validate_result(result, output_path, "subtitle extraction")
        return "ssa" if codec == "ssa" else "ass"

    async def normalize_external(
        self,
        *,
        source_path: Path,
        codec_name: str | None,
        output_path: Path,
    ) -> str:
        codec = codec_name.casefold() if codec_name is not None else ""
        if codec not in _TEXT_SUBTITLE_CODECS:
            raise UnsupportedSubtitleCodecError(
                "Subtitle codec is not supported for ASS normalization: "
                f"{codec_name or 'unknown'}",
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        encoder = "copy" if codec in {"ass", "ssa"} else "ass"

        result = await self._runner.run(
            (
                self._executable,
                "-v",
                "error",
                "-y",
                "-i",
                str(source_path),
                "-c:s",
                encoder,
                str(output_path),
            ),
        )
        _validate_result(result, output_path, "subtitle normalization")
        return "ssa" if codec == "ssa" else "ass"


def _validate_result(
    result: FFmpegCommandResult,
    output_path: Path,
    operation: str,
) -> None:
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise SubtitleProcessingError(
            message
            or f"FFmpeg {operation} failed with exit code {result.returncode}",
        )
    if not output_path.is_file():
        raise SubtitleProcessingError(
            f"FFmpeg completed without creating subtitle output: {output_path}",
        )


class FFmpegAttachmentProcessingError(RuntimeError):
    pass


class FFmpegAttachmentProcessor:
    def __init__(
        self,
        *,
        executable: str = "ffmpeg",
        runner: FFmpegRunner | None = None,
    ) -> None:
        self._executable = executable
        self._runner = runner or SubprocessFFmpegRunner()

    async def extract(
        self,
        *,
        media_path: Path,
        attachment_index: int,
        output_path: Path,
    ) -> None:
        if attachment_index < 0:
            raise FFmpegAttachmentProcessingError(
                f"Attachment index must be non-negative: {attachment_index}",
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = await self._runner.run(
            (
                self._executable,
                "-v",
                "error",
                "-y",
                f"-dump_attachment:t:{attachment_index}",
                str(output_path),
                "-i",
                str(media_path),
                "-map",
                f"0:t:{attachment_index}",
                "-c",
                "copy",
                "-f",
                "null",
                "-",
            ),
        )
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", errors="replace").strip()
            raise FFmpegAttachmentProcessingError(
                message
                or "FFmpeg attachment extraction failed with exit code "
                f"{result.returncode}",
            )
        if not output_path.is_file():
            raise FFmpegAttachmentProcessingError(
                f"FFmpeg completed without creating attachment output: {output_path}",
            )


class FFmpegPlayableMediaProcessingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PlayableMediaProcessingResult:
    output_path: Path
    operation: PlayableMediaOperation


class FFmpegPlayableMediaProcessor:
    def __init__(
        self,
        *,
        executable: str = "ffmpeg",
        runner: FFmpegRunner | None = None,
    ) -> None:
        self._executable = executable
        self._runner = runner or SubprocessFFmpegRunner()

    async def process(
        self,
        *,
        media_path: Path,
        output_path: Path,
        operation: PlayableMediaOperation,
    ) -> PlayableMediaProcessingResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if operation is PlayableMediaOperation.REMUX:
            video_codec = "copy"
            audio_codec = "copy"
        else:
            video_codec = "libx265"
            audio_codec = "aac"

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
                "0:a?",
                "-map_chapters",
                "0",
                "-sn",
                "-dn",
                "-c:v",
                video_codec,
                "-tag:v",
                "hvc1",
                "-c:a",
                audio_codec,
                *(( "-b:a", "192k") if operation is PlayableMediaOperation.TRANSCODE else ()),
                *(( "-preset", "medium", "-crf", "28", "-pix_fmt", "yuv420p")
                  if operation is PlayableMediaOperation.TRANSCODE
                  else ()),
                "-movflags",
                "+faststart",
                str(output_path),
            ),
        )

        if result.returncode != 0:
            message = result.stderr.decode("utf-8", errors="replace").strip()
            raise FFmpegPlayableMediaProcessingError(
                message
                or "FFmpeg playable media processing failed with exit code "
                f"{result.returncode}",
            )
        if not output_path.is_file():
            raise FFmpegPlayableMediaProcessingError(
                f"FFmpeg completed without creating playable output: {output_path}",
            )

        return PlayableMediaProcessingResult(
            output_path=output_path,
            operation=operation,
        )
