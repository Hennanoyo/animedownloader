from collections.abc import Awaitable, Sequence
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
        self.progress: list[float] = []

    async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
        return self._record(args)

    async def run_with_progress(
        self,
        args: Sequence[str],
        *,
        duration_seconds: float,
        on_progress: Awaitable | object,
    ) -> FFmpegCommandResult:
        del duration_seconds
        result = self._record(args)
        callback = on_progress
        for percent in (20.0, 60.0, 100.0):
            self.progress.append(percent)
            await callback(percent)  # type: ignore[operator]
        return result

    def _record(self, args: Sequence[str]) -> FFmpegCommandResult:
        command = tuple(args)
        self.calls.append(command)
        for value in command:
            path = Path(value)
            if path.suffix in {".mp4", ".jpg"}:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"output")
        return FFmpegCommandResult(stdout=b"", stderr=b"", returncode=0)


@pytest.mark.anyio
async def test_preparation_uses_one_ffmpeg_process_for_playable_and_thumbnail(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mkv"
    playable = tmp_path / "playable.mp4"
    sprite = tmp_path / "sprite.jpg"
    vtt = tmp_path / "sprite.vtt"
    source.write_bytes(b"source")

    runner = FakeRunner()
    processor = FFmpegMediaPreparationProcessor(runner=runner)
    progress: list[float] = []

    async def on_progress(percent: float) -> None:
        progress.append(percent)

    result = await processor.process(
        media_path=source,
        playable_path=playable,
        sprite_path=sprite,
        vtt_path=vtt,
        duration_seconds=12.0,
        operation=PlayableMediaOperation.TRANSCODE,
        on_progress=on_progress,
    )

    assert isinstance(result, MediaPreparationProcessingResult)
    assert len(runner.calls) == 1
    command = runner.calls[0]
    assert "-filter_complex" in command
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "split=2" in filter_graph
    assert "tile=15x12" in filter_graph
    assert command[command.index("-c:v") + 1] == "libx265"
    assert command[command.index("-threads") + 1] == "8"
    assert str(playable) in command
    assert str(sprite) in command

    assert result.playable.output_path == playable
    assert result.thumbnail.sprite_path == sprite
    assert result.thumbnail.vtt_path == vtt
    assert result.thumbnail.frame_count == 3
    assert vtt.read_text(encoding="utf-8").startswith("WEBVTT\n")
    assert progress == [20.0, 60.0, 100.0]


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
async def test_preparation_remuxes_playable_and_decodes_thumbnail_in_one_process(
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
    assert command[command.index("-c:v:0") + 1] == "copy"
    assert "-filter_complex" in command
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "fps=" in filter_graph
    assert "tile=15x12" in filter_graph
    assert str(playable) in command
    assert str(sprite) in command


@pytest.mark.anyio
async def test_preparation_propagates_ffmpeg_failure(tmp_path: Path) -> None:
    source = tmp_path / "source.mkv"
    source.write_bytes(b"source")

    class FailedRunner:
        async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
            del args
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
