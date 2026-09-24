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
        command = tuple(args)
        self.calls.append(command)

        output = Path(command[-1])
        if "%05d" in command[-1]:
            output.parent.mkdir(parents=True, exist_ok=True)
            for index in range(1, 4):
                output.with_name(f"frame-{index:05d}.jpg").write_bytes(b"frame")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"output")

        return FFmpegCommandResult(stdout=b"", stderr=b"", returncode=0)


@pytest.mark.anyio
async def test_preparation_transcodes_and_generates_thumbnail_in_separate_processes(
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
    assert len(runner.calls) == 3

    playable_command = runner.calls[0]
    assert "-filter_complex" not in playable_command
    assert playable_command[playable_command.index("-c:v") + 1] == "libx265"
    assert playable_command[playable_command.index("-threads") + 1] == "8"
    assert playable_command[-1] == str(playable)

    extraction_command = runner.calls[1]
    assert "-vf" in extraction_command
    assert "fps=" in extraction_command[extraction_command.index("-vf") + 1]
    assert extraction_command[-1].endswith("frame-%05d.jpg")

    sprite_command = runner.calls[2]
    assert "-vf" in sprite_command
    assert sprite_command[sprite_command.index("-vf") + 1].startswith("tile=15x12")
    assert sprite_command[-1] == str(sprite)

    assert result.playable.output_path == playable
    assert result.thumbnail.sprite_path == sprite
    assert result.thumbnail.vtt_path == vtt
    assert result.thumbnail.frame_count == 3
    assert vtt.read_text(encoding="utf-8").startswith("WEBVTT\n")


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
    assert command[command.index("-pix_fmt") + 1] == "yuv420p"
    assert command[command.index("-preset") + 1] == "p5"
    assert command[command.index("-rc") + 1] == "vbr"
    assert command[command.index("-cq") + 1] == "28"
    assert command[command.index("-b:v") + 1] == "0"


@pytest.mark.anyio
async def test_preparation_remuxes_and_generates_thumbnail_in_separate_processes(
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

    assert len(runner.calls) == 3
    playable_command = runner.calls[0]
    assert "-filter_complex" not in playable_command
    assert playable_command[playable_command.index("-c:v") + 1] == "copy"
    assert playable_command[-1] == str(playable)

    assert runner.calls[1][-1].endswith("frame-%05d.jpg")
    assert runner.calls[2][-1] == str(sprite)


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
