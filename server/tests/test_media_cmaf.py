from collections.abc import Sequence
from pathlib import Path

import pytest
from animedownloader_media import (
    CMAFMediaSegment,
    CMAFRepresentationMetadata,
    FFmpegCMAFProcessor,
    FFmpegCommandResult,
    build_dash_manifest,
    build_hls_master_playlist,
)


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
        self.calls.append(tuple(args))
        playlist_path = Path(args[-1])
        playlist_path.parent.mkdir(parents=True, exist_ok=True)
        (playlist_path.parent / "s").mkdir(parents=True, exist_ok=True)
        (playlist_path.parent / "init.mp4").write_bytes(b"init")
        (playlist_path.parent / "s" / "00000.m4s").write_bytes(b"segment")
        playlist_path.write_text(
            "#EXTM3U\n"
            "#EXT-X-VERSION:7\n"
            "#EXT-X-TARGETDURATION:2\n"
            "#EXT-X-MEDIA-SEQUENCE:0\n"
            "#EXT-X-PLAYLIST-TYPE:VOD\n"
            '#EXT-X-MAP:URI="init.mp4"\n'
            "#EXTINF:1.5,\n"
            "s/00000.m4s\n"
            "#EXT-X-ENDLIST\n",
            encoding="utf-8",
        )
        return FFmpegCommandResult(stdout=b"", stderr=b"", returncode=0)


@pytest.mark.anyio
async def test_cmaf_processor_creates_one_fmp4_media_set(tmp_path: Path) -> None:
    source = tmp_path / "playable.mp4"
    output = tmp_path / "1080p"
    source.write_bytes(b"source")

    runner = FakeRunner()
    result = await FFmpegCMAFProcessor(runner=runner).process(
        media_path=source,
        output_dir=output,
    )

    assert len(runner.calls) == 1
    command = runner.calls[0]
    assert command[command.index("-hls_segment_type") + 1] == "fmp4"
    assert command[command.index("-hls_segment_filename") + 1] == "s/%05d.m4s"
    assert result.init_segment_path == output / "init.mp4"
    assert result.segments == (
        CMAFMediaSegment(
            number=0,
            duration_seconds=1.5,
            uri="s/00000.m4s",
        ),
    )


def test_hls_master_and_dash_manifest_reference_same_representation() -> None:
    representation = CMAFRepresentationMetadata(
        quality="1080p",
        width=1920,
        height=1080,
        bandwidth=2_000_000,
        video_codec="hevc",
        audio_codec="aac",
        duration_seconds=2.0,
        init_uri="1080p/init.mp4",
        segment_template="1080p/s/$Number%05d$.m4s",
        segments=(CMAFMediaSegment(0, 2.0, "s/00000.m4s"),),
    )

    hls = build_hls_master_playlist((representation,))
    dash = build_dash_manifest(
        (representation,),
        media_presentation_duration_seconds=2.0,
    )

    assert "1080p/index.m3u8" in hls
    assert 'initialization="1080p/init.mp4"' in dash
    assert 'media="1080p/s/$Number%05d$.m4s"' in dash


@pytest.mark.anyio
async def test_cmaf_processor_propagates_ffmpeg_failure(tmp_path: Path) -> None:
    class FailedRunner:
        async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
            return FFmpegCommandResult(
                stdout=b"",
                stderr=b"packaging failed",
                returncode=1,
            )

    source = tmp_path / "playable.mp4"
    source.write_bytes(b"source")

    with pytest.raises(RuntimeError, match="packaging failed"):
        await FFmpegCMAFProcessor(runner=FailedRunner()).process(
            media_path=source,
            output_dir=tmp_path / "1080p",
        )


@pytest.mark.anyio
async def test_cmaf_processor_normalizes_absolute_ffmpeg_segment_paths(
    tmp_path: Path,
) -> None:
    class AbsolutePathRunner:
        async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
            playlist_path = Path(args[-1])
            segment_path = playlist_path.parent / "s" / "00000.m4s"
            playlist_path.parent.mkdir(parents=True, exist_ok=True)
            segment_path.parent.mkdir(parents=True, exist_ok=True)
            (playlist_path.parent / "init.mp4").write_bytes(b"init")
            segment_path.write_bytes(b"segment")
            playlist_path.write_text(
                "#EXTM3U\n"
                "#EXT-X-TARGETDURATION:2\n"
                '#EXT-X-MAP:URI="init.mp4"\n'
                "#EXTINF:1.5,\n"
                "00000.m4s\n"
                "#EXT-X-ENDLIST\n",
                encoding="utf-8",
            )
            return FFmpegCommandResult(stdout=b"", stderr=b"", returncode=0)

    result = await FFmpegCMAFProcessor(
        runner=AbsolutePathRunner(),
    ).process(
        media_path=tmp_path / "source.mp4",
        output_dir=tmp_path / "1080p",
    )

    assert result.segments[0].uri == "s/00000.m4s"
    assert "s/00000.m4s" in result.playlist_path.read_text(
        encoding="utf-8",
    )
