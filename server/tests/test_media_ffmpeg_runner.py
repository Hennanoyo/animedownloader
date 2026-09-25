import asyncio
import sys
from pathlib import Path

import pytest
from animedownloader_media import FFmpegTimeoutError, SubprocessFFmpegRunner


@pytest.mark.skipif(sys.platform == "win32", reason="requires POSIX process groups")
@pytest.mark.anyio
async def test_timeout_kills_ffmpeg_process_group(tmp_path: Path) -> None:
    marker = tmp_path / "grandchild-survived"
    child_code = (
        "import pathlib, sys, time; "
        "time.sleep(0.8); "
        "pathlib.Path(sys.argv[1]).write_text('alive', encoding='utf-8')"
    )
    parent_code = (
        "import subprocess, sys, time; "
        "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]]); "
        "time.sleep(10)"
    )

    runner = SubprocessFFmpegRunner(
        timeout_seconds=0.2,
        heartbeat_interval_seconds=0.05,
    )

    with pytest.raises(FFmpegTimeoutError):
        await runner.run(
            (
                sys.executable,
                "-c",
                parent_code,
                child_code,
                str(marker),
            ),
        )

    await asyncio.sleep(1.0)
    assert not marker.exists()


@pytest.mark.anyio
async def test_ffmpeg_progress_parser_reports_input_timeline() -> None:
    from animedownloader_media.ffmpeg import consume_ffmpeg_progress

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
