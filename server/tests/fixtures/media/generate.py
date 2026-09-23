from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


DURATION_SECONDS = 12
WIDTH = 320
HEIGHT = 180


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a small deterministic MKV fixture for media pipeline tests.",
    )
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    generate_fixture(args.output)


def generate_fixture(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="animedownloader-fixture-") as temp:
        workdir = Path(temp)
        base_media = workdir / "base.mkv"
        subtitle = workdir / "subtitle.ass"
        metadata = workdir / "chapters.txt"
        attachment = workdir / "Example.ttf"

        subtitle.write_text(
            """[Script Info]
ScriptType: v4.00+
PlayResX: 320
PlayResY: 180

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,18,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,10,,Fixture subtitle one
Dialogue: 0,0:00:06.00,0:00:10.00,Default,,0,0,10,,Fixture subtitle two
""",
            encoding="utf-8",
        )

        metadata.write_text(
            """;FFMETADATA1
[CHAPTER]
TIMEBASE=1/1000
START=0
END=4000
title=Opening

[CHAPTER]
TIMEBASE=1/1000
START=4000
END=8000
title=Main

[CHAPTER]
TIMEBASE=1/1000
START=8000
END=12000
title=Ending
""",
            encoding="utf-8",
        )

        # The attachment is intentionally tiny and deterministic. Its purpose is
        # to exercise Matroska attachment extraction, not font rendering.
        attachment.write_bytes(b"ANIMEDOWNLOADER-TEST-FONT\n")

        _run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"testsrc2=size={WIDTH}x{HEIGHT}:rate=24:duration={DURATION_SECONDS}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=440:sample_rate=48000:duration={DURATION_SECONDS}",
                "-c:v",
                "mpeg4",
                "-q:v",
                "6",
                "-c:a",
                "aac",
                "-shortest",
                str(base_media),
            ]
        )

        _run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(base_media),
                "-i",
                str(subtitle),
                "-i",
                str(metadata),
                "-map",
                "0",
                "-map",
                "1:0",
                "-map_chapters",
                "2",
                "-c",
                "copy",
                "-c:s",
                "ass",
                "-metadata:s:s:0",
                "language=eng",
                "-metadata:s:s:0",
                "title=Fixture English",
                "-attach",
                str(attachment),
                "-metadata:s:t:0",
                "mimetype=application/x-truetype-font",
                "-metadata:s:t:0",
                "filename=Example.ttf",
                str(output),
            ]
        )


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
