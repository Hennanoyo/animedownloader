from dataclasses import dataclass, field
from pathlib import Path

import pytest
from animedownloader_media import (
    FFmpegCommandResult,
    FFmpegSubtitleProcessor,
    UnsupportedSubtitleCodecError,
)


@dataclass
class FakeRunner:
    result: FFmpegCommandResult
    calls: list[tuple[str, ...]] = field(default_factory=list)

    async def run(self, args: tuple[str, ...]) -> FFmpegCommandResult:
        self.calls.append(args)
        output_path = Path(args[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.result.returncode == 0:
            output_path.touch()
        return self.result


@pytest.mark.anyio
async def test_extract_preserves_ass_without_reencoding(tmp_path: Path) -> None:
    runner = FakeRunner(FFmpegCommandResult(b"", b"", 0))
    processor = FFmpegSubtitleProcessor(runner=runner)
    output_path = tmp_path / "track.ass"

    normalized_format = await processor.extract(
        media_path=tmp_path / "episode.mkv",
        stream_index=2,
        codec_name="ass",
        output_path=output_path,
    )

    assert normalized_format == "ass"
    assert runner.calls == [
        (
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(tmp_path / "episode.mkv"),
            "-map",
            "0:2",
            "-c:s",
            "copy",
            str(output_path),
        ),
    ]
    assert output_path.is_file()


@pytest.mark.anyio
async def test_extract_normalizes_subrip_to_ass(tmp_path: Path) -> None:
    runner = FakeRunner(FFmpegCommandResult(b"", b"", 0))
    processor = FFmpegSubtitleProcessor(runner=runner)
    output_path = tmp_path / "track.ass"

    normalized_format = await processor.extract(
        media_path=tmp_path / "episode.mkv",
        stream_index=4,
        codec_name="subrip",
        output_path=output_path,
    )

    assert normalized_format == "ass"
    assert runner.calls[-1][-2:] == ("ass", str(output_path))


@pytest.mark.anyio
async def test_normalize_external_supports_webvtt(tmp_path: Path) -> None:
    runner = FakeRunner(FFmpegCommandResult(b"", b"", 0))
    processor = FFmpegSubtitleProcessor(runner=runner)
    output_path = tmp_path / "track.ass"
    source_path = tmp_path / "track.vtt"

    normalized_format = await processor.normalize_external(
        source_path=source_path,
        codec_name="webvtt",
        output_path=output_path,
    )

    assert normalized_format == "ass"
    assert runner.calls[-1] == (
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        str(source_path),
        "-c:s",
        "ass",
        str(output_path),
    )


@pytest.mark.anyio
async def test_extract_rejects_bitmap_subtitles(tmp_path: Path) -> None:
    processor = FFmpegSubtitleProcessor(
        runner=FakeRunner(FFmpegCommandResult(b"", b"", 0)),
    )

    with pytest.raises(UnsupportedSubtitleCodecError, match="hdmv_pgs_subtitle"):
        await processor.extract(
            media_path=tmp_path / "episode.mkv",
            stream_index=5,
            codec_name="hdmv_pgs_subtitle",
            output_path=tmp_path / "track.ass",
        )


@pytest.mark.anyio
async def test_extract_surfaces_ffmpeg_error(tmp_path: Path) -> None:
    runner = FakeRunner(
        FFmpegCommandResult(b"", b"invalid subtitle stream", 1),
    )
    processor = FFmpegSubtitleProcessor(runner=runner)

    with pytest.raises(RuntimeError, match="invalid subtitle stream"):
        await processor.extract(
            media_path=tmp_path / "episode.mkv",
            stream_index=2,
            codec_name="subrip",
            output_path=tmp_path / "track.ass",
        )
