from __future__ import annotations

import asyncio
import os
import shlex
import signal
import sys
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from .playback import PlayableMediaOperation

DEFAULT_FFMPEG_TIMEOUT_SECONDS = 1800.0
DEFAULT_FFMPEG_HEARTBEAT_INTERVAL_SECONDS = 30.0


def build_video_encoder_options(video_encoder: str) -> tuple[str, ...]:
    if video_encoder == "libx265":
        return (
            "-c:v",
            "libx265",
            "-preset",
            "medium",
            "-crf",
            "28",
            "-threads",
            "8",
            "-pix_fmt",
            "yuv420p",
        )
    if video_encoder == "hevc_nvenc":
        return (
            "-c:v",
            "hevc_nvenc",
            "-preset",
            "p5",
            "-rc",
            "vbr",
            "-cq",
            "28",
            "-b:v",
            "0",
            "-pix_fmt",
            "yuv420p",
        )
    raise ValueError(
        "Unsupported video encoder: "
        f"{video_encoder!r}; expected 'libx265' or 'hevc_nvenc'",
    )


@dataclass(frozen=True, slots=True)
class FFmpegCommandResult:
    stdout: bytes
    stderr: bytes
    returncode: int


class FFmpegRunner(Protocol):
    async def run(self, args: Sequence[str]) -> FFmpegCommandResult: ...


FFmpegProgressCallback = Callable[[float], Awaitable[None]]


@runtime_checkable
class FFmpegProgressRunner(Protocol):
    async def run_with_progress(
        self,
        args: Sequence[str],
        *,
        duration_seconds: float,
        on_progress: FFmpegProgressCallback,
    ) -> FFmpegCommandResult: ...


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
            start_new_session=(sys.platform != "win32"),
        )
        print(
            f"[worker] FFmpeg started: pid={process.pid} command={shlex.join(command)}",
            flush=True,
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
                    print(
                        f"[worker] FFmpeg still running: pid={process.pid} elapsed={elapsed:.0f}s",
                        flush=True,
                    )

            elapsed = time.monotonic() - started_at
            returncode = process.returncode or 0
            print(
                f"[worker] FFmpeg finished: pid={process.pid} "
                f"elapsed={elapsed:.1f}s returncode={returncode}",
                flush=True,
            )
            return FFmpegCommandResult(
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
            )
        except TimeoutError as exc:
            await _terminate_process(process)
            await communication
            elapsed = time.monotonic() - started_at
            print(
                f"[worker] FFmpeg timed out: pid={process.pid} "
                f"elapsed={elapsed:.1f}s timeout={self._timeout_seconds:.1f}s "
                f"command={shlex.join(command)}",
                flush=True,
                file=sys.stderr,
            )
            raise FFmpegTimeoutError(
                "FFmpeg timed out after "
                f"{self._timeout_seconds:.1f}s: {shlex.join(command)}",
            ) from exc
        except asyncio.CancelledError:
            await _terminate_process(process)
            await communication
            print(
                f"[worker] FFmpeg cancelled: pid={process.pid}",
                flush=True,
                file=sys.stderr,
            )
            raise


    async def run_with_progress(
        self,
        args: Sequence[str],
        *,
        duration_seconds: float,
        on_progress: FFmpegProgressCallback,
    ) -> FFmpegCommandResult:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")

        command = tuple(args)
        progress_command = (
            command[0],
            "-nostats",
            "-progress",
            "pipe:1",
            *command[1:],
        )
        started_at = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            *progress_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=(sys.platform != "win32"),
        )
        print(
            "[worker] FFmpeg started with progress: "
            f"pid={process.pid} command={shlex.join(progress_command)}",
            flush=True,
        )

        progress_task = asyncio.create_task(
            _consume_ffmpeg_progress(
                process.stdout,
                duration_seconds=duration_seconds,
                on_progress=on_progress,
            ),
        )
        stderr_task = asyncio.create_task(process.stderr.read())
        wait_task = asyncio.create_task(process.wait())
        try:
            while not wait_task.done():
                elapsed = time.monotonic() - started_at
                remaining = self._timeout_seconds - elapsed
                if remaining <= 0:
                    raise TimeoutError

                try:
                    await asyncio.wait_for(
                        asyncio.shield(wait_task),
                        timeout=min(self._heartbeat_interval_seconds, remaining),
                    )
                except asyncio.TimeoutError:
                    elapsed = time.monotonic() - started_at
                    print(
                        f"[worker] FFmpeg still running: pid={process.pid} "
                        f"elapsed={elapsed:.0f}s",
                        flush=True,
                    )

            progress_output, stderr = await asyncio.gather(
                progress_task,
                stderr_task,
            )
            elapsed = time.monotonic() - started_at
            returncode = process.returncode or 0
            print(
                f"[worker] FFmpeg finished: pid={process.pid} "
                f"elapsed={elapsed:.1f}s returncode={returncode}",
                flush=True,
            )
            return FFmpegCommandResult(
                stdout=progress_output,
                stderr=stderr,
                returncode=returncode,
            )
        except TimeoutError as exc:
            await _terminate_process(process)
            await asyncio.gather(progress_task, stderr_task, return_exceptions=True)
            elapsed = time.monotonic() - started_at
            print(
                f"[worker] FFmpeg timed out: pid={process.pid} "
                f"elapsed={elapsed:.1f}s timeout={self._timeout_seconds:.1f}s "
                f"command={shlex.join(progress_command)}",
                flush=True,
                file=sys.stderr,
            )
            raise FFmpegTimeoutError(
                "FFmpeg timed out after "
                f"{self._timeout_seconds:.1f}s: {shlex.join(progress_command)}",
            ) from exc
        except asyncio.CancelledError:
            await _terminate_process(process)
            await asyncio.gather(progress_task, stderr_task, return_exceptions=True)
            print(
                f"[worker] FFmpeg cancelled: pid={process.pid}",
                flush=True,
                file=sys.stderr,
            )
            raise


async def _consume_ffmpeg_progress(
    stdout: asyncio.StreamReader,
    *,
    duration_seconds: float,
    on_progress: FFmpegProgressCallback,
) -> bytes:
    last_percent = -1.0
    last_emitted_at = 0.0
    output = bytearray()
    while True:
        line = await stdout.readline()
        if not line:
            break
        output.extend(line)

        decoded = line.decode("utf-8", errors="replace").strip()
        if "=" not in decoded:
            continue
        key, value = decoded.split("=", 1)

        percent: float | None = None
        if key == "out_time_us":
            try:
                elapsed_seconds = max(0.0, float(value) / 1_000_000.0)
            except ValueError:
                continue
            percent = min(100.0, elapsed_seconds / duration_seconds * 100.0)
        elif key == "progress" and value == "end":
            percent = 100.0

        if percent is None:
            continue

        now = time.monotonic()
        if percent < 100.0 and (
            now - last_emitted_at < 0.25
            and percent - last_percent < 0.5
        ):
            continue

        try:
            await on_progress(percent)
        except Exception:
            print(
                f"[worker] FFmpeg progress callback failed: progress={percent:.1f}",
                flush=True,
                file=sys.stderr,
            )
            continue

        last_percent = percent
        last_emitted_at = now

    return bytes(output)


async def run_ffmpeg(
    runner: FFmpegRunner,
    args: Sequence[str],
    *,
    duration_seconds: float | None = None,
    on_progress: FFmpegProgressCallback | None = None,
) -> FFmpegCommandResult:
    if (
        on_progress is not None
        and duration_seconds is not None
        and duration_seconds > 0
        and isinstance(runner, FFmpegProgressRunner)
    ):
        return await runner.run_with_progress(
            args,
            duration_seconds=duration_seconds,
            on_progress=on_progress,
        )
    return await runner.run(args)

async def probe_video_encoder(
    video_encoder: str,
    *,
    executable: str = "ffmpeg",
    runner: FFmpegRunner | None = None,
) -> bool:
    if video_encoder != "hevc_nvenc":
        raise ValueError(
            "Video encoder probe only supports 'hevc_nvenc'",
        )

    probe_runner = runner or SubprocessFFmpegRunner(
        timeout_seconds=15.0,
        heartbeat_interval_seconds=5.0,
    )
    try:
        result = await probe_runner.run(
            (
                executable,
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=1920x1080:rate=1",
                "-frames:v",
                "2",
                "-an",
                "-c:v",
                "hevc_nvenc",
                "-preset",
                "p5",
                "-rc",
                "vbr",
                "-cq",
                "28",
                "-b:v",
                "0",
                "-pix_fmt",
                "yuv420p",
                "-f",
                "null",
                "-",
            ),
        )
    except (FFmpegTimeoutError, OSError) as exc:
        print(
            "[worker] NVENC probe unavailable: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        return False

    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        print(
            "[worker] NVENC probe failed: "
            f"returncode={result.returncode} error={message or 'unknown'}",
            flush=True,
        )
        return False
    return True


async def resolve_video_encoder(
    video_encoder: str,
    *,
    executable: str = "ffmpeg",
    runner: FFmpegRunner | None = None,
) -> str:
    if video_encoder != "auto":
        build_video_encoder_options(video_encoder)
        return video_encoder

    nvenc_available = await probe_video_encoder(
        "hevc_nvenc",
        executable=executable,
        runner=runner,
    )
    selected = "hevc_nvenc" if nvenc_available else "libx265"
    print(
        f"[worker] video encoder auto-detected: "
        f"{selected} (nvenc_available={nvenc_available})",
        flush=True,
    )
    return selected


async def _terminate_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return

    if sys.platform == "win32":
        process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return

    await process.wait()


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
        video_encoder: str = "libx265",
    ) -> None:
        self._executable = executable
        self._runner = runner or SubprocessFFmpegRunner()
        self._video_encoder = video_encoder
        build_video_encoder_options(video_encoder)

    async def process(
        self,
        *,
        media_path: Path,
        output_path: Path,
        operation: PlayableMediaOperation,
        duration_seconds: float | None = None,
        on_progress: FFmpegProgressCallback | None = None,
    ) -> PlayableMediaProcessingResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if operation is PlayableMediaOperation.REMUX:
            video_options = ("-c:v", "copy")
            audio_codec = "copy"
        else:
            video_options = build_video_encoder_options(self._video_encoder)
            audio_codec = "aac"

        result = await run_ffmpeg(
            self._runner,
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
                *video_options,
                "-tag:v",
                "hvc1",
                "-c:a",
                audio_codec,
                *(( "-b:a", "192k") if operation is PlayableMediaOperation.TRANSCODE else ()),
                "-movflags",
                "+faststart",
                str(output_path),
            ),
            duration_seconds=duration_seconds,
            on_progress=on_progress,
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
