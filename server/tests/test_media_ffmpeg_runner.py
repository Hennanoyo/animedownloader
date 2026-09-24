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
