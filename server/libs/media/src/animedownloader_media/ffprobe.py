from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .errors import MediaProbeError
from .models import MediaProbe
from .parser import parse_ffprobe_json


@dataclass(frozen=True, slots=True)
class ProbeCommandResult:
    stdout: bytes
    stderr: bytes
    returncode: int


class ProbeRunner(Protocol):
    async def run(self, args: Sequence[str]) -> ProbeCommandResult: ...


class SubprocessProbeRunner:
    async def run(self, args: Sequence[str]) -> ProbeCommandResult:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return ProbeCommandResult(
            stdout=stdout,
            stderr=stderr,
            returncode=process.returncode or 0,
        )


class FFprobeInspector:
    def __init__(
        self,
        *,
        executable: str = "ffprobe",
        runner: ProbeRunner | None = None,
    ) -> None:
        self._executable = executable
        self._runner = runner or SubprocessProbeRunner()

    async def inspect(self, path: Path) -> MediaProbe:
        if not path.is_file():
            raise MediaProbeError(f"Media file does not exist: {path}")

        result = await self._runner.run(
            (
                self._executable,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_error",
                "-show_format",
                "-show_streams",
                "-show_chapters",
                str(path),
            )
        )

        if result.returncode != 0:
            message = result.stderr.decode("utf-8", errors="replace").strip()
            raise MediaProbeError(
                message or f"FFprobe failed with exit code {result.returncode} for {path}"
            )

        return parse_ffprobe_json(result.stdout, path)
