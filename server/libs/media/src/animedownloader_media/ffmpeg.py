from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FFmpegCommandResult:
    stdout: bytes
    stderr: bytes
    returncode: int


class FFmpegRunner(Protocol):
    async def run(self, args: Sequence[str]) -> FFmpegCommandResult: ...


class SubprocessFFmpegRunner:
    async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return FFmpegCommandResult(
            stdout=stdout,
            stderr=stderr,
            returncode=process.returncode or 0,
        )


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
