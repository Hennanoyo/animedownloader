from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid7

import pytest
from animedownloader_media import (
    MediaFormat,
    MediaProbe,
    MediaStream,
    MediaStreamType,
    PlayableMediaOperation,
    PlayableMediaPlanner,
    PlayableMediaProcessingResult,
)
from animedownloader_media_processing import MediaTranscodingJobStatus
from animedownloader_worker.media_transcoding import (
    MediaTranscodingContext,
    MediaTranscodingRunner,
)


@dataclass
class FakeState:
    context: MediaTranscodingContext
    transitions: list[str] = field(default_factory=list)
    completed_path: Path | None = None
    failed_message: str | None = None

    async def load(self, job_id: UUID) -> MediaTranscodingContext:
        return self.context

    async def mark_processing(
        self,
        job_id: UUID,
        operation: PlayableMediaOperation,
    ) -> None:
        self.transitions.append(operation.value)
        self.context = MediaTranscodingContext(
            job_id=self.context.job_id,
            asset_id=self.context.asset_id,
            source_path=self.context.source_path,
            source_metadata_updated_at=self.context.source_metadata_updated_at,
            status=MediaTranscodingJobStatus.PROCESSING,
            operation=operation,
            variant_id=self.context.variant_id,
        )

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        output_path: Path,
        probe: MediaProbe,
    ) -> None:
        self.completed_path = output_path
        self.context = MediaTranscodingContext(
            job_id=self.context.job_id,
            asset_id=self.context.asset_id,
            source_path=self.context.source_path,
            source_metadata_updated_at=self.context.source_metadata_updated_at,
            status=MediaTranscodingJobStatus.COMPLETED,
            operation=self.context.operation,
            variant_id=self.context.variant_id,
        )

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        self.failed_message = error_message


class FakeInspector:
    def __init__(self, probes: list[MediaProbe | Exception]) -> None:
        self.probes = list(probes)
        self.paths: list[Path] = []

    async def inspect(self, path: Path) -> MediaProbe:
        self.paths.append(path)
        result = self.probes.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeProcessor:
    def __init__(self) -> None:
        self.operations: list[PlayableMediaOperation] = []

    async def process(
        self,
        *,
        media_path: Path,
        output_path: Path,
        operation: PlayableMediaOperation,
    ) -> PlayableMediaProcessingResult:
        self.operations.append(operation)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"playable")
        return PlayableMediaProcessingResult(
            output_path=output_path,
            operation=operation,
        )


def make_probe(codec: str, container: str) -> MediaProbe:
    return MediaProbe(
        path="/downloads/source.mkv",
        format=MediaFormat(
            filename="/downloads/source.mkv",
            format_name=container,
            format_long_name=None,
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
                codec_name=codec,
                codec_long_name=None,
                profile=None,
                codec_tag_string=None,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                frame_rate="24/1",
                duration_seconds=60.0,
                bit_rate=1000000,
                channels=None,
                channel_layout=None,
                sample_rate_hz=None,
                language=None,
                title=None,
                disposition_default=True,
                disposition_forced=False,
                tags=(),
            ),
            MediaStream(
                index=1,
                codec_type=MediaStreamType.AUDIO,
                codec_name="aac",
                codec_long_name=None,
                profile=None,
                codec_tag_string=None,
                width=None,
                height=None,
                pixel_format=None,
                frame_rate=None,
                duration_seconds=60.0,
                bit_rate=192000,
                channels=2,
                channel_layout="stereo",
                sample_rate_hz=48000,
                language=None,
                title=None,
                disposition_default=True,
                disposition_forced=False,
                tags=(),
            ),
        ),
        chapters=(),
    )


def make_context(
    *,
    status: MediaTranscodingJobStatus,
    operation: PlayableMediaOperation | None = None,
) -> MediaTranscodingContext:
    return MediaTranscodingContext(
        job_id=uuid7(),
        asset_id=uuid7(),
        source_path="/downloads/source/source.mkv",
        source_metadata_updated_at=datetime(2026, 9, 24),
        status=status,
        operation=operation,
        variant_id=uuid7(),
    )


@pytest.mark.anyio
async def test_runner_transcodes_incompatible_source(tmp_path: Path) -> None:
    source_probe = make_probe("mpeg4", "matroska,webm")
    output_probe = make_probe("hevc", "mov,mp4,m4a,3gp,3g2,mj2")
    state = FakeState(make_context(status=MediaTranscodingJobStatus.PENDING))
    inspector = FakeInspector([source_probe, output_probe])
    processor = FakeProcessor()

    runner = MediaTranscodingRunner(
        state=state,
        inspector=inspector,
        planner=PlayableMediaPlanner(),
        processor=processor,
        media_root=tmp_path,
    )

    await runner.run(state.context.job_id)

    assert state.transitions == ["transcode"]
    assert processor.operations == [PlayableMediaOperation.TRANSCODE]
    assert state.completed_path is not None
    assert inspector.paths == [
        Path("/downloads/source/source.mkv"),
        state.completed_path,
    ]


@pytest.mark.anyio
async def test_runner_remuxes_compatible_source(tmp_path: Path) -> None:
    source_probe = make_probe("hevc", "mov,mp4,m4a,3gp,3g2,mj2")
    output_probe = source_probe
    state = FakeState(make_context(status=MediaTranscodingJobStatus.PENDING))
    inspector = FakeInspector([source_probe, output_probe])
    processor = FakeProcessor()

    runner = MediaTranscodingRunner(
        state=state,
        inspector=inspector,
        planner=PlayableMediaPlanner(),
        processor=processor,
        media_root=tmp_path,
    )

    await runner.run(state.context.job_id)

    assert state.transitions == ["remux"]
    assert processor.operations == [PlayableMediaOperation.REMUX]


@pytest.mark.anyio
async def test_runner_persists_failure(tmp_path: Path) -> None:
    state = FakeState(make_context(status=MediaTranscodingJobStatus.PENDING))
    inspector = FakeInspector([RuntimeError("probe failed")])
    processor = FakeProcessor(PlayableMediaOperation.TRANSCODE)

    runner = MediaTranscodingRunner(
        state=state,
        inspector=inspector,
        planner=PlayableMediaPlanner(),
        processor=processor,
        media_root=tmp_path,
    )

    with pytest.raises(RuntimeError, match="probe failed"):
        await runner.run(state.context.job_id)

    assert state.failed_message == "probe failed"

@pytest.mark.anyio
async def test_runner_rejects_stale_source_snapshot(tmp_path: Path) -> None:
    state = FakeState(
        make_context(status=MediaTranscodingJobStatus.PENDING),
    )
    state.context = MediaTranscodingContext(
        job_id=state.context.job_id,
        asset_id=state.context.asset_id,
        source_path=state.context.source_path,
        source_metadata_updated_at=state.context.source_metadata_updated_at,
        status=state.context.status,
        operation=state.context.operation,
        variant_id=state.context.variant_id,
        source_is_current=False,
    )
    processor = FakeProcessor()
    inspector = FakeInspector([])

    runner = MediaTranscodingRunner(
        state=state,
        inspector=inspector,
        planner=PlayableMediaPlanner(),
        processor=processor,
        media_root=tmp_path,
    )

    with pytest.raises(
        RuntimeError,
        match="source changed after the transcoding job",
    ):
        await runner.run(state.context.job_id)

    assert state.failed_message is not None
    assert inspector.paths == []
    assert processor.operations == []
