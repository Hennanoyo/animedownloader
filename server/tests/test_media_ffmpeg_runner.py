import asyncio
import os
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


@pytest.mark.skipif(sys.platform == "win32", reason="requires executable POSIX script")
@pytest.mark.anyio
async def test_ffmpeg_progress_runner_reports_input_timeline(tmp_path: Path) -> None:
    executable = tmp_path / "fake-ffmpeg"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import time\n"
        "print('out_time_us=1000000', flush=True)\n"
        "print('progress=continue', flush=True)\n"
        "time.sleep(0.01)\n"
        "print('out_time_us=5000000', flush=True)\n"
        "print('progress=end', flush=True)\n",
        encoding="utf-8",
    )
    executable.chmod(executable.stat().st_mode | os.X_OK)

    progress: list[float] = []

    async def on_progress(percent: float) -> None:
        progress.append(percent)

    result = await SubprocessFFmpegRunner(
        timeout_seconds=2.0,
        heartbeat_interval_seconds=0.1,
    ).run_with_progress(
        (str(executable),),
        duration_seconds=5.0,
        on_progress=on_progress,
    )

    assert result.returncode == 0
    assert progress == [20.0, 100.0]
