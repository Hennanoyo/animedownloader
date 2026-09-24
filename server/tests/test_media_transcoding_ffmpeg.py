from collections.abc import Sequence
from pathlib import Path

import pytest
from animedownloader_media import (
    FFmpegCommandResult,
    FFmpegPlayableMediaProcessingError,
    FFmpegPlayableMediaProcessor,
    PlayableMediaOperation,
    resolve_video_encoder,
)


class ProbeRunner:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.calls: list[tuple[str, ...]] = []

    async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
        self.calls.append(tuple(args))
        return FFmpegCommandResult(b"", b"", self.returncode)


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
        command = tuple(args)
        self.calls.append(command)
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"playable")
        return FFmpegCommandResult(b"", b"", 0)


@pytest.mark.anyio
async def test_auto_encoder_prefers_nvenc_when_probe_succeeds() -> None:
    runner = ProbeRunner(returncode=0)

    encoder = await resolve_video_encoder("auto", runner=runner)

    assert encoder == "hevc_nvenc"
    assert runner.calls
    command = runner.calls[0]
    assert "hevc_nvenc" in command
    assert "-frames:v" in command
    assert command[command.index("-frames:v") + 1] == "2"
    assert command[-3:] == ("-f", "null", "-")


@pytest.mark.anyio
async def test_auto_encoder_falls_back_to_cpu_when_probe_raises_os_error() -> None:
    class FailingProbeRunner:
        async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
            raise OSError("GPU runtime unavailable")

    encoder = await resolve_video_encoder(
        "auto",
        runner=FailingProbeRunner(),
    )

    assert encoder == "libx265"


@pytest.mark.anyio
async def test_auto_encoder_falls_back_to_cpu_when_nvenc_probe_fails() -> None:
    runner = ProbeRunner(returncode=1)

    encoder = await resolve_video_encoder("auto", runner=runner)

    assert encoder == "libx265"
    assert runner.calls


@pytest.mark.anyio
async def test_transcode_command_uses_hevc_and_aac(tmp_path: Path) -> None:
    output_path = tmp_path / "playable.mp4"
    runner = FakeRunner()

    result = await FFmpegPlayableMediaProcessor(runner=runner).process(
        media_path=tmp_path / "episode.mkv",
        output_path=output_path,
        operation=PlayableMediaOperation.TRANSCODE,
    )

    command = runner.calls[0]
    assert result.output_path == output_path
    assert "-c:v" in command
    assert "libx265" in command
    assert command[command.index("-threads") + 1] == "8"
    assert "-c:a" in command
    assert "aac" in command
    assert "-tag:v" in command
    assert "hvc1" in command
    assert "-movflags" in command
    assert "+faststart" in command


@pytest.mark.anyio
async def test_transcode_command_can_use_nvenc(tmp_path: Path) -> None:
    output_path = tmp_path / "playable.mp4"
    runner = FakeRunner()

    await FFmpegPlayableMediaProcessor(
        runner=runner,
        video_encoder="hevc_nvenc",
    ).process(
        media_path=tmp_path / "episode.mkv",
        output_path=output_path,
        operation=PlayableMediaOperation.TRANSCODE,
    )

    command = runner.calls[0]
    assert command[command.index("-c:v") + 1] == "hevc_nvenc"
    assert command[command.index("-preset") + 1] == "p5"
    assert command[command.index("-pix_fmt") + 1] == "yuv420p"
    assert command[command.index("-rc") + 1] == "vbr"
    assert command[command.index("-cq") + 1] == "28"
    assert command[command.index("-b:v") + 1] == "0"


@pytest.mark.anyio
async def test_remux_command_copies_streams(tmp_path: Path) -> None:
    output_path = tmp_path / "playable.mp4"
    runner = FakeRunner()

    await FFmpegPlayableMediaProcessor(runner=runner).process(
        media_path=tmp_path / "episode.mkv",
        output_path=output_path,
        operation=PlayableMediaOperation.REMUX,
    )

    command = runner.calls[0]
    assert "-c:v" in command
    assert command[command.index("-c:v") + 1] == "copy"
    assert "-c:a" in command
    assert command[command.index("-c:a") + 1] == "copy"


@pytest.mark.anyio
async def test_ffmpeg_failure_raises(tmp_path: Path) -> None:
    class FailingRunner(FakeRunner):
        async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
            self.calls.append(tuple(args))
            return FFmpegCommandResult(b"", b"encoder failed", 1)

    with pytest.raises(FFmpegPlayableMediaProcessingError, match="encoder failed"):
        await FFmpegPlayableMediaProcessor(runner=FailingRunner()).process(
            media_path=tmp_path / "episode.mkv",
            output_path=tmp_path / "playable.mp4",
            operation=PlayableMediaOperation.REMUX,
        )
