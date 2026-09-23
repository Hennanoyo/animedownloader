from collections.abc import Sequence
from pathlib import Path

import pytest
from animedownloader_media import (
    FFmpegCommandResult,
    FFmpegThumbnailProcessingError,
    FFmpegThumbnailSpriteProcessor,
)


class FakeRunner:
    def __init__(self, frame_count: int = 5) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.frame_count = frame_count

    async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
        command = tuple(args)
        self.calls.append(command)

        output_path = Path(command[-1])
        if "%05d" in str(output_path):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            for index in range(1, self.frame_count + 1):
                frame_path = output_path.parent / f"frame-{index:05d}.jpg"
                frame_path.write_bytes(f"frame-{index}".encode())
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"sprite")

        return FFmpegCommandResult(b"", b"", 0)


@pytest.mark.anyio
async def test_generates_sprite_and_webvtt(tmp_path: Path) -> None:
    media_path = tmp_path / "episode.mkv"
    media_path.write_bytes(b"media")
    output_dir = tmp_path / "thumbnails"
    runner = FakeRunner()

    result = await FFmpegThumbnailSpriteProcessor(runner=runner).generate(
        media_path=media_path,
        output_dir=output_dir,
        duration_seconds=25.0,
    )

    assert result.frame_count == 5
    assert result.interval_seconds == 5.0
    assert result.sprite_path == output_dir / "sprite.jpg"
    assert result.vtt_path == output_dir / "sprite.vtt"
    assert result.sprite_path.read_bytes() == b"sprite"
    assert result.vtt_path.read_text(encoding="utf-8") == (
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:05.000\n"
        "sprite.jpg#xywh=0,0,160,90\n\n"
        "00:00:05.000 --> 00:00:10.000\n"
        "sprite.jpg#xywh=160,0,160,90\n\n"
        "00:00:10.000 --> 00:00:15.000\n"
        "sprite.jpg#xywh=320,0,160,90\n\n"
        "00:00:15.000 --> 00:00:20.000\n"
        "sprite.jpg#xywh=480,0,160,90\n\n"
        "00:00:20.000 --> 00:00:25.000\n"
        "sprite.jpg#xywh=640,0,160,90\n\n"
    )
    assert runner.calls[0][0] == "ffmpeg"
    assert "-vf" in runner.calls[0]
    assert runner.calls[1][0] == "ffmpeg"
    assert "tile=15x12:padding=0:margin=0" in runner.calls[1]


@pytest.mark.anyio
async def test_requires_positive_media_duration(tmp_path: Path) -> None:
    media_path = tmp_path / "episode.mkv"
    media_path.write_bytes(b"media")

    with pytest.raises(
        FFmpegThumbnailProcessingError,
        match="positive media duration",
    ):
        await FFmpegThumbnailSpriteProcessor().generate(
            media_path=media_path,
            output_dir=tmp_path / "thumbnails",
            duration_seconds=None,
        )


@pytest.mark.anyio
async def test_fails_when_ffmpeg_does_not_create_frames(tmp_path: Path) -> None:
    media_path = tmp_path / "episode.mkv"
    media_path.write_bytes(b"media")

    class EmptyRunner(FakeRunner):
        async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
            command = tuple(args)
            self.calls.append(command)
            return FFmpegCommandResult(b"", b"", 0)

    with pytest.raises(
        FFmpegThumbnailProcessingError,
        match="thumbnail frames",
    ):
        await FFmpegThumbnailSpriteProcessor(runner=EmptyRunner()).generate(
            media_path=media_path,
            output_dir=tmp_path / "thumbnails",
            duration_seconds=10.0,
        )
