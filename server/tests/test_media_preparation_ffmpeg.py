from collections.abc import Sequence
from pathlib import Path

import pytest
from animedownloader_media import (
    FFmpegCommandResult,
    FFmpegMediaPreparationProcessor,
    MediaPreparationProcessingResult,
    PlayableMediaOperation,
)


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
        self.calls.append(tuple(args))
        playable_path = Path(args[-8])
        sprite_path = Path(args[-1])
        playable_path.parent.mkdir(parents=True, exist_ok=True)
        sprite_path.parent.mkdir(parents=True, exist_ok=True)
        playable_path.write_bytes(b"playable")
        sprite_path.write_bytes(b"sprite")
        return FFmpegCommandResult(stdout=b"", stderr=b"", returncode=0)


@pytest.mark.anyio
async def test_preparation_transcodes_and_generates_thumbnail_in_one_process(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mkv"
    playable = tmp_path / "playable.mp4"
    sprite = tmp_path / "sprite.jpg"
    vtt = tmp_path / "sprite.vtt"
    source.write_bytes(b"source")

    runner = FakeRunner()
    processor = FFmpegMediaPreparationProcessor(runner=runner)

    result = await processor.process(
        media_path=source,
        playable_path=playable,
        sprite_path=sprite,
        vtt_path=vtt,
        duration_seconds=12.0,
        operation=PlayableMediaOperation.TRANSCODE,
    )

    assert isinstance(result, MediaPreparationProcessingResult)
    assert len(runner.calls) == 1
    command = runner.calls[0]
    assert command[command.index("-filter_complex_threads") + 1] == "2"
    assert "-filter_buffered_frames" not in command
    assert "-filter_complex" in command
    assert "split=2[playable][thumbnail]" in command[command.index("-filter_complex") + 1]
    assert command.count("-map") == 3
    assert result.playable.output_path == playable
    assert result.thumbnail.sprite_path == sprite
    assert result.thumbnail.vtt_path == vtt
    assert result.thumbnail.frame_count == 3
    assert vtt.read_text(encoding="utf-8").startswith("WEBVTT\n")


@pytest.mark.anyio
async def test_preparation_can_use_cuda_decode(tmp_path: Path) -> None:
    source = tmp_path / "source.mkv"
    playable = tmp_path / "playable.mp4"
    sprite = tmp_path / "sprite.jpg"
    vtt = tmp_path / "sprite.vtt"
    source.write_bytes(b"source")

    runner = FakeRunner()
    processor = FFmpegMediaPreparationProcessor(
        runner=runner,
        video_encoder="hevc_nvenc",
        hardware_acceleration="cuda",
    )

    await processor.process(
        media_path=source,
        playable_path=playable,
        sprite_path=sprite,
        vtt_path=vtt,
        duration_seconds=12.0,
        operation=PlayableMediaOperation.TRANSCODE,
    )

    command = runner.calls[0]
    input_index = command.index("-i")
    assert command[input_index - 4 : input_index] == (
        "-hwaccel",
        "cuda",
        "-hwaccel_output_format",
        "cuda",
    )
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "[thumbnail]hwdownload,format=nv12," in filter_graph
    assert "-pix_fmt" not in command


@pytest.mark.anyio
async def test_preparation_can_use_nvenc_for_transcode(tmp_path: Path) -> None:
    source = tmp_path / "source.mkv"
    playable = tmp_path / "playable.mp4"
    sprite = tmp_path / "sprite.jpg"
    vtt = tmp_path / "sprite.vtt"
    source.write_bytes(b"source")

    runner = FakeRunner()
    processor = FFmpegMediaPreparationProcessor(
        runner=runner,
        video_encoder="hevc_nvenc",
    )

    await processor.process(
        media_path=source,
        playable_path=playable,
        sprite_path=sprite,
        vtt_path=vtt,
        duration_seconds=12.0,
        operation=PlayableMediaOperation.TRANSCODE,
    )

    command = runner.calls[0]
    assert command[command.index("-c:v") + 1] == "hevc_nvenc"
    assert command[command.index("-preset") + 1] == "p5"
    assert command[command.index("-rc") + 1] == "vbr"
    assert command[command.index("-cq") + 1] == "28"
    assert command[command.index("-b:v") + 1] == "0"


@pytest.mark.anyio
async def test_preparation_remuxes_and_generates_thumbnail_in_one_process(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mp4"
    playable = tmp_path / "playable.mp4"
    sprite = tmp_path / "sprite.jpg"
    vtt = tmp_path / "sprite.vtt"
    source.write_bytes(b"source")

    runner = FakeRunner()
    processor = FFmpegMediaPreparationProcessor(runner=runner)

    await processor.process(
        media_path=source,
        playable_path=playable,
        sprite_path=sprite,
        vtt_path=vtt,
        duration_seconds=12.0,
        operation=PlayableMediaOperation.REMUX,
    )

    assert len(runner.calls) == 1
    command = runner.calls[0]
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "split=2" not in filter_graph
    assert "0:v:0" in command
    assert command[command.index("-c:v") + 1] == "copy"
    assert command[-1] == str(sprite)


@pytest.mark.anyio
async def test_preparation_propagates_ffmpeg_failure(tmp_path: Path) -> None:
    source = tmp_path / "source.mkv"
    source.write_bytes(b"source")

    class FailedRunner:
        async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
            return FFmpegCommandResult(
                stdout=b"",
                stderr=b"encoder failed",
                returncode=1,
            )

    processor = FFmpegMediaPreparationProcessor(runner=FailedRunner())

    with pytest.raises(RuntimeError, match="encoder failed"):
        await processor.process(
            media_path=source,
            playable_path=tmp_path / "playable.mp4",
            sprite_path=tmp_path / "sprite.jpg",
            vtt_path=tmp_path / "sprite.vtt",
            duration_seconds=12.0,
            operation=PlayableMediaOperation.TRANSCODE,
        )
