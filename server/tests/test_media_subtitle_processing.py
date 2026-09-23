from collections.abc import Sequence
from pathlib import Path

import pytest
from animedownloader_media import (
    FFmpegAttachmentProcessor,
    FFmpegCommandResult,
)


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    async def run(self, args: Sequence[str]) -> FFmpegCommandResult:
        command = tuple(args)
        self.calls.append(command)
        output_path = Path(command[5])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"font-data")
        return FFmpegCommandResult(b"", b"", 0)


@pytest.mark.anyio
async def test_extract_attachment_uses_attachment_stream_specifier(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()
    processor = FFmpegAttachmentProcessor(runner=runner)
    output_path = tmp_path / "font.ttf"

    await processor.extract(
        media_path=tmp_path / "episode.mkv",
        attachment_index=1,
        output_path=output_path,
    )

    assert runner.calls == [
        (
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-dump_attachment:t:1",
            str(output_path),
            "-i",
            str(tmp_path / "episode.mkv"),
        ),
    ]
    assert output_path.read_bytes() == b"font-data"
