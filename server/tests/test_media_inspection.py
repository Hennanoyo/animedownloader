import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from animedownloader_media import (
    FFprobeInspector,
    MediaProbeError,
    MediaStreamType,
    ProbeCommandResult,
)


class FakeProbeRunner:
    def __init__(self, result: ProbeCommandResult) -> None:
        self.result = result
        self.args: tuple[str, ...] | None = None

    async def run(self, args: Sequence[str]) -> ProbeCommandResult:
        self.args = tuple(args)
        return self.result


def probe_payload() -> bytes:
    return json.dumps(
        {
            "format": {
                "filename": "/downloads/episode.mkv",
                "format_name": "matroska,webm",
                "format_long_name": "Matroska / WebM",
                "start_time": "0.000000",
                "duration": "123.456000",
                "size": "123456789",
                "bit_rate": "7999999",
                "tags": {"ENCODER": "libmatroska"},
            },
            "streams": [
                {
                    "index": 0,
                    "codec_name": "hevc",
                    "codec_long_name": "H.265 / HEVC",
                    "profile": "Main 10",
                    "codec_type": "video",
                    "codec_tag_string": "[0][0][0][0]",
                    "width": 1920,
                    "height": 1080,
                    "pix_fmt": "yuv420p10le",
                    "r_frame_rate": "24000/1001",
                    "duration": "123.456000",
                    "bit_rate": "7000000",
                    "disposition": {"default": 1, "forced": 0},
                    "tags": {"language": "jpn", "title": "Japanese Video"},
                },
                {
                    "index": 1,
                    "codec_name": "aac",
                    "codec_long_name": "AAC",
                    "codec_type": "audio",
                    "channels": 2,
                    "channel_layout": "stereo",
                    "sample_rate": "48000",
                    "duration": "123.400000",
                    "bit_rate": "192000",
                    "disposition": {"default": 1},
                    "tags": {"language": "jpn", "title": "Japanese"},
                },
                {
                    "index": 2,
                    "codec_name": "ass",
                    "codec_long_name": "ASS (Advanced SubStation Alpha) subtitle",
                    "codec_type": "subtitle",
                    "disposition": {"default": 1},
                    "tags": {"language": "kor", "title": "Korean"},
                },
                {
                    "index": 3,
                    "codec_name": "ttf",
                    "codec_long_name": "TrueType Font",
                    "codec_type": "attachment",
                    "tags": {"filename": "NotoSansCJK-Regular.ttc"},
                },
            ],
            "chapters": [
                {
                    "id": 1,
                    "start_time": "0.000000",
                    "end_time": "12.345000",
                    "tags": {"title": "Opening"},
                }
            ],
        }
    ).encode()


@pytest.mark.anyio
async def test_inspector_parses_media_streams_and_chapters(tmp_path: Path) -> None:
    media_path = tmp_path / "episode.mkv"
    media_path.touch()
    runner = FakeProbeRunner(ProbeCommandResult(stdout=probe_payload(), stderr=b"", returncode=0))

    result = await FFprobeInspector(runner=runner).inspect(media_path)

    assert result.path == str(media_path)
    assert result.format.format_name == "matroska,webm"
    assert result.format.duration_seconds == pytest.approx(123.456)
    assert result.format.size_bytes == 123456789
    assert result.video_streams[0].codec_name == "hevc"
    assert result.video_streams[0].width == 1920
    assert result.video_streams[0].height == 1080
    assert result.video_streams[0].codec_type is MediaStreamType.VIDEO
    assert result.audio_streams[0].channels == 2
    assert result.audio_streams[0].sample_rate_hz == 48000
    assert result.subtitle_streams[0].language == "kor"
    assert result.attachment_streams[0].codec_name == "ttf"
    assert result.chapters[0].title == "Opening"

    assert runner.args is not None
    assert runner.args[:8] == (
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_error",
        "-show_format",
        "-show_streams",
    )
    assert runner.args[8] == "-show_chapters"
    assert runner.args[9] == str(media_path)


@pytest.mark.anyio
async def test_inspector_raises_for_missing_media_file(tmp_path: Path) -> None:
    runner = FakeProbeRunner(ProbeCommandResult(stdout=b"{}", stderr=b"", returncode=0))

    with pytest.raises(MediaProbeError, match="does not exist"):
        await FFprobeInspector(runner=runner).inspect(tmp_path / "missing.mkv")

    assert runner.args is None


@pytest.mark.anyio
async def test_inspector_raises_for_ffprobe_failure(tmp_path: Path) -> None:
    media_path = tmp_path / "episode.mkv"
    media_path.touch()
    runner = FakeProbeRunner(
        ProbeCommandResult(
            stdout=b"",
            stderr=b"Invalid data found when processing input",
            returncode=1,
        )
    )

    with pytest.raises(MediaProbeError, match="Invalid data found"):
        await FFprobeInspector(runner=runner).inspect(media_path)


@pytest.mark.anyio
async def test_inspector_raises_for_invalid_json(tmp_path: Path) -> None:
    media_path = tmp_path / "episode.mkv"
    media_path.touch()
    runner = FakeProbeRunner(ProbeCommandResult(stdout=b"not-json", stderr=b"", returncode=0))

    with pytest.raises(MediaProbeError, match="Invalid FFprobe JSON"):
        await FFprobeInspector(runner=runner).inspect(media_path)
