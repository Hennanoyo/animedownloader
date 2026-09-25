import asyncio
from pathlib import Path

import pytest
from animedownloader_media import FFmpegTimeoutError, SubprocessFFmpegRunner


@pytest.mark.anyio
async def test_ffmpeg_progress_parser_reports_input_timeline() -> None:
    from animedownloader_media.ffmpeg import _consume_ffmpeg_progress

    stdout = asyncio.StreamReader()
    stdout.feed_data(b"out_time_us=1000000\n")
    stdout.feed_data(b"progress=continue\n")
    stdout.feed_data(b"out_time_us=5000000\n")
    stdout.feed_data(b"progress=end\n")
    stdout.feed_eof()

    progress: list[float] = []

    async def on_progress(percent: float) -> None:
        progress.append(percent)

    result = await _consume_ffmpeg_progress(
        stdout,
        duration_seconds=5.0,
        on_progress=on_progress,
    )

    assert result == (
        b"out_time_us=1000000\n"
        b"progress=continue\n"
        b"out_time_us=5000000\n"
        b"progress=end\n"
    )
    assert progress == [20.0, 100.0]
