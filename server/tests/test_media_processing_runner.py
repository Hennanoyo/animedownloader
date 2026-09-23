from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid7

import pytest
from animedownloader_media import (
    MediaChapter,
    MediaFormat,
    MediaProbe,
    MediaStream,
    MediaStreamType,
)
from animedownloader_media_processing import MediaProcessingJobStatus
from animedownloader_worker.media_processing import (
    MediaProcessingContext,
    MediaProcessingExecutionError,
    MediaProcessingRunner,
)


def _strings() -> list[str]:
    return []


def _paths() -> list[Path]:
    return []


@dataclass
class FakeState:
    context: MediaProcessingContext
    transitions: list[str] = field(default_factory=_strings)
    completed: tuple[str, dict[str, object]] | None = None
    failed_message: str | None = None

    async def load(self, job_id: UUID) -> MediaProcessingContext:
        return self.context

    async def mark_processing(self, job_id: UUID) -> None:
        self.transitions.append("processing")
        self.context = MediaProcessingContext(
            status=MediaProcessingJobStatus.PROCESSING,
            download_directory=self.context.download_directory,
        )

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        media_path: str,
        probe_metadata: dict[str, object],
    ) -> None:
        self.completed = (media_path, probe_metadata)
        self.context = MediaProcessingContext(
            status=MediaProcessingJobStatus.COMPLETED,
            download_directory=self.context.download_directory,
        )

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        self.failed_message = error_message
        self.context = MediaProcessingContext(
            status=MediaProcessingJobStatus.FAILED,
            download_directory=self.context.download_directory,
        )


@dataclass
class FakeInspector:
    result: MediaProbe | Exception
    paths: list[Path] = field(default_factory=_paths)

    async def inspect(self, path: Path) -> MediaProbe:
        self.paths.append(path)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def make_probe(path: Path) -> MediaProbe:
    return MediaProbe(
        path=str(path),
        format=MediaFormat(
            filename=str(path),
            format_name="matroska,webm",
            format_long_name="Matroska / WebM",
            start_time_seconds=0.0,
            duration_seconds=60.0,
            size_bytes=1024,
            bit_rate=1000,
            tags=(),
        ),
        streams=(
            MediaStream(
                index=0,
                codec_type=MediaStreamType.VIDEO,
                codec_name="hevc",
                codec_long_name=None,
                profile=None,
                codec_tag_string=None,
                width=1920,
                height=1080,
                pixel_format="yuv420p10le",
                frame_rate="24000/1001",
                duration_seconds=60.0,
                bit_rate=900,
                channels=None,
                channel_layout=None,
                sample_rate_hz=None,
                language=None,
                title=None,
                disposition_default=True,
                disposition_forced=False,
                tags=(),
            ),
        ),
        chapters=(
            MediaChapter(
                id=1,
                start_time_seconds=0.0,
                end_time_seconds=60.0,
                title="Episode",
            ),
        ),
    )


@pytest.mark.anyio
async def test_runner_inspects_and_completes(tmp_path: Path) -> None:
    job_id = uuid7()
    download_job_id = uuid7()
    media_path = tmp_path / str(download_job_id) / "episode.mkv"
    media_path.parent.mkdir()
    media_path.touch()

    state = FakeState(
        MediaProcessingContext(
            status=MediaProcessingJobStatus.PENDING,
            download_directory=str(download_job_id),
        )
    )
    inspector = FakeInspector(make_probe(media_path))
    runner = MediaProcessingRunner(
        state=state,
        inspector=inspector,
        download_root=tmp_path,
    )

    await runner.run(job_id)

    assert state.transitions == ["processing"]
    assert inspector.paths == [media_path]
    assert state.completed is not None
    assert state.completed[0] == str(media_path)
    format_metadata = state.completed[1]["format"]
    assert isinstance(format_metadata, dict)
    assert format_metadata["format_name"] == "matroska,webm"


@pytest.mark.anyio
async def test_runner_fails_when_media_file_is_missing(tmp_path: Path) -> None:
    job_id = uuid7()
    download_job_id = uuid7()
    state = FakeState(
        MediaProcessingContext(
            status=MediaProcessingJobStatus.PENDING,
            download_directory=str(download_job_id),
        )
    )
    inspector = FakeInspector(make_probe(tmp_path / "unused.mkv"))
    runner = MediaProcessingRunner(
        state=state,
        inspector=inspector,
        download_root=tmp_path,
    )

    with pytest.raises(MediaProcessingExecutionError, match="does not exist"):
        await runner.run(job_id)

    assert state.failed_message is not None
    assert inspector.paths == []


@pytest.mark.anyio
async def test_runner_marks_probe_failure(tmp_path: Path) -> None:
    job_id = uuid7()
    download_job_id = uuid7()
    media_path = tmp_path / str(download_job_id) / "episode.mkv"
    media_path.parent.mkdir()
    media_path.touch()

    state = FakeState(
        MediaProcessingContext(
            status=MediaProcessingJobStatus.PENDING,
            download_directory=str(download_job_id),
        )
    )
    inspector = FakeInspector(RuntimeError("invalid media"))
    runner = MediaProcessingRunner(
        state=state,
        inspector=inspector,
        download_root=tmp_path,
    )

    with pytest.raises(RuntimeError, match="invalid media"):
        await runner.run(job_id)

    assert state.failed_message == "invalid media"


@pytest.mark.anyio
async def test_runner_rejects_multiple_media_files(tmp_path: Path) -> None:
    job_id = uuid7()
    download_job_id = uuid7()
    root = tmp_path / str(download_job_id)
    root.mkdir()
    (root / "episode-1.mkv").touch()
    (root / "episode-2.mkv").touch()

    state = FakeState(
        MediaProcessingContext(
            status=MediaProcessingJobStatus.PENDING,
            download_directory=str(download_job_id),
        )
    )
    inspector = FakeInspector(make_probe(root / "episode-1.mkv"))
    runner = MediaProcessingRunner(
        state=state,
        inspector=inspector,
        download_root=tmp_path,
    )

    with pytest.raises(MediaProcessingExecutionError, match="Expected exactly one"):
        await runner.run(job_id)

    assert state.failed_message is not None
    assert inspector.paths == []
