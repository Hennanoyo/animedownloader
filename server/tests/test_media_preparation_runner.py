from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid7

import pytest
from animedownloader_media import (
    MediaFormat,
    MediaPreparationProcessingResult,
    MediaProbe,
    MediaStream,
    MediaStreamType,
    PlayableMediaOperation,
    PlayableMediaPlanner,
    PlayableMediaProcessingResult,
    ThumbnailSpriteResult,
)
from animedownloader_media_processing import (
    MediaPreparationJobStatus,
    MediaTranscodingOperation,
)
from animedownloader_storage import LocalStorage
from animedownloader_worker.media_preparation import (
    MediaPreparationContext,
    MediaPreparationRunner,
)


class FakeState:
    def __init__(self, context: MediaPreparationContext) -> None:
        self.context = context
        self.process_calls: list[tuple[MediaTranscodingOperation | None, bool, bool]] = []
        self.completed: tuple[MediaProbe | None, ThumbnailSpriteResult | None] | None = None
        self.failed_message: str | None = None

    async def load(self, job_id: UUID) -> MediaPreparationContext:
        return self.context

    async def update_operation(
        self,
        job_id: UUID,
        *,
        operation: MediaTranscodingOperation | None,
    ) -> None:
        self.context = MediaPreparationContext(
            job_id=self.context.job_id,
            asset_id=self.context.asset_id,
            source_path=self.context.source_path,
            source_metadata_updated_at=self.context.source_metadata_updated_at,
            status=self.context.status,
            operation=operation,
            variant_id=self.context.variant_id,
            playable_ready=self.context.playable_ready,
            thumbnail_ready=self.context.thumbnail_ready,
            duration_seconds=self.context.duration_seconds,
            source_is_current=self.context.source_is_current,
        )

    async def mark_processing(
        self,
        job_id: UUID,
        *,
        operation: MediaTranscodingOperation | None,
        playable_required: bool,
        thumbnail_required: bool,
    ) -> None:
        self.process_calls.append((operation, playable_required, thumbnail_required))
        self.context = MediaPreparationContext(
            job_id=self.context.job_id,
            asset_id=self.context.asset_id,
            source_path=self.context.source_path,
            source_metadata_updated_at=self.context.source_metadata_updated_at,
            status=MediaPreparationJobStatus.PROCESSING,
            operation=operation,
            variant_id=self.context.variant_id,
            playable_ready=self.context.playable_ready,
            thumbnail_ready=self.context.thumbnail_ready,
            duration_seconds=self.context.duration_seconds,
            source_is_current=self.context.source_is_current,
        )

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        playable_probe: MediaProbe | None,
        playable_output_key: str | None,
        thumbnail: ThumbnailSpriteResult | None,
        thumbnail_sprite_key: str | None,
        thumbnail_vtt_key: str | None,
    ) -> None:
        self.completed = (playable_probe, thumbnail)

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


class FakePreparationProcessor:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path, Path, Path, float | None, PlayableMediaOperation]] = []

    async def process(
        self,
        *,
        media_path: Path,
        playable_path: Path,
        sprite_path: Path,
        vtt_path: Path,
        duration_seconds: float | None,
        operation: PlayableMediaOperation,
    ) -> MediaPreparationProcessingResult:
        self.calls.append(
            (
                media_path,
                playable_path,
                sprite_path,
                vtt_path,
                duration_seconds,
                operation,
            )
        )
        playable_path.parent.mkdir(parents=True, exist_ok=True)
        playable_path.write_bytes(b"playable")
        sprite_path.parent.mkdir(parents=True, exist_ok=True)
        sprite_path.write_bytes(b"sprite")
        vtt_path.write_text("WEBVTT\n", encoding="utf-8")
        return MediaPreparationProcessingResult(
            playable=PlayableMediaProcessingResult(
                output_path=playable_path,
                operation=operation,
            ),
            thumbnail=ThumbnailSpriteResult(
                sprite_path=sprite_path,
                vtt_path=vtt_path,
                frame_count=3,
                interval_seconds=5.0,
            ),
        )


class FakePlayableProcessor:
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


class FakeThumbnailProcessor:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(
        self,
        *,
        media_path: Path,
        output_dir: Path,
        duration_seconds: float | None,
    ) -> ThumbnailSpriteResult:
        self.calls += 1
        output_dir.mkdir(parents=True, exist_ok=True)
        sprite = output_dir / "sprite.jpg"
        vtt = output_dir / "sprite.vtt"
        sprite.write_bytes(b"sprite")
        vtt.write_text("WEBVTT\n", encoding="utf-8")
        return ThumbnailSpriteResult(
            sprite_path=sprite,
            vtt_path=vtt,
            frame_count=3,
            interval_seconds=5.0,
        )


def make_probe(codec: str, container: str) -> MediaProbe:
    return MediaProbe(
        path="/downloads/source.mkv",
        format=MediaFormat(
            filename="/downloads/source.mkv",
            format_name=container,
            format_long_name=None,
            start_time_seconds=0.0,
            duration_seconds=12.0,
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
                duration_seconds=12.0,
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
                duration_seconds=12.0,
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
    playable_ready: bool = False,
    thumbnail_ready: bool = False,
    source_is_current: bool = True,
) -> MediaPreparationContext:
    return MediaPreparationContext(
        job_id=uuid7(),
        asset_id=uuid7(),
        source_path="/downloads/source.mkv",
        source_metadata_updated_at=datetime(2026, 9, 24),
        status=MediaPreparationJobStatus.PENDING,
        operation=None,
        variant_id=uuid7(),
        playable_ready=playable_ready,
        thumbnail_ready=thumbnail_ready,
        duration_seconds=12.0,
        source_is_current=source_is_current,
    )


def make_runner(
    tmp_path: Path,
    state: FakeState,
    inspector: FakeInspector,
    preparation: FakePreparationProcessor,
    playable: FakePlayableProcessor,
    thumbnail: FakeThumbnailProcessor,
) -> MediaPreparationRunner:
    return MediaPreparationRunner(
        state=state,
        inspector=inspector,
        planner=PlayableMediaPlanner(),
        preparation_processor=preparation,
        playable_processor=playable,
        thumbnail_processor=thumbnail,
        storage=LocalStorage(tmp_path / "storage", "http://localhost:8888"),
    )


@pytest.mark.anyio
async def test_runner_combines_playable_and_thumbnail_generation(tmp_path: Path) -> None:
    state = FakeState(make_context())
    source_probe = make_probe("mpeg4", "matroska,webm")
    output_probe = make_probe("hevc", "mov,mp4,m4a,3gp,3g2,mj2")
    inspector = FakeInspector([source_probe, output_probe])
    preparation = FakePreparationProcessor()
    playable = FakePlayableProcessor()
    thumbnail = FakeThumbnailProcessor()

    runner = make_runner(tmp_path, state, inspector, preparation, playable, thumbnail)

    await runner.run(state.context.job_id)

    assert state.process_calls == [
        (MediaTranscodingOperation.TRANSCODE, True, True),
    ]
    assert len(preparation.calls) == 1
    assert preparation.calls[0][-1] is PlayableMediaOperation.TRANSCODE
    assert playable.operations == []
    assert thumbnail.calls == 0
    assert state.completed is not None
    assert state.completed[0] is output_probe
    assert state.completed[1] is not None
    playable = (
        tmp_path
        / "storage"
        / "playable"
        / str(state.context.asset_id)
        / f"{state.context.variant_id}.mp4"
    )
    sprite = tmp_path / "storage" / "thumbnails" / str(state.context.asset_id) / "sprite.jpg"
    vtt = tmp_path / "storage" / "thumbnails" / str(state.context.asset_id) / "sprite.vtt"
    assert playable.read_bytes() == b"playable"
    assert sprite.read_bytes() == b"sprite"
    assert vtt.read_text(encoding="utf-8") == "WEBVTT\n"
    assert not (
        tmp_path
        / "storage"
        / "playable"
        / str(state.context.asset_id)
        / f"{state.context.job_id}.mp4"
    ).exists()
    assert len(inspector.paths) == 2


@pytest.mark.anyio
async def test_runner_refreshes_stale_operation_on_resume(tmp_path: Path) -> None:
    context = make_context()
    state = FakeState(
        MediaPreparationContext(
            job_id=context.job_id,
            asset_id=context.asset_id,
            source_path=context.source_path,
            source_metadata_updated_at=context.source_metadata_updated_at,
            status=MediaPreparationJobStatus.PROCESSING,
            operation=MediaTranscodingOperation.TRANSCODE,
            variant_id=context.variant_id,
            playable_ready=False,
            thumbnail_ready=False,
            duration_seconds=context.duration_seconds,
            source_is_current=True,
        ),
    )
    source_probe = make_probe("hevc", "matroska,webm")
    output_probe = make_probe("hevc", "mov,mp4,m4a,3gp,3g2,mj2")
    inspector = FakeInspector([source_probe, output_probe])
    preparation = FakePreparationProcessor()
    playable = FakePlayableProcessor()
    thumbnail = FakeThumbnailProcessor()

    runner = make_runner(tmp_path, state, inspector, preparation, playable, thumbnail)

    await runner.run(state.context.job_id)

    assert state.context.operation is MediaTranscodingOperation.REMUX
    assert state.completed is not None
    assert len(preparation.calls) == 1
    assert preparation.calls[0][-1] is PlayableMediaOperation.REMUX


@pytest.mark.anyio
async def test_runner_reuses_completed_playable_for_thumbnail_retry(tmp_path: Path) -> None:
    state = FakeState(
        make_context(playable_ready=True, thumbnail_ready=False),
    )
    inspector = FakeInspector([])
    preparation = FakePreparationProcessor()
    playable = FakePlayableProcessor()
    thumbnail = FakeThumbnailProcessor()

    runner = make_runner(tmp_path, state, inspector, preparation, playable, thumbnail)

    await runner.run(state.context.job_id)

    assert state.process_calls == [
        (None, False, True),
    ]
    assert inspector.paths == []
    assert preparation.calls == []
    assert playable.operations == []
    assert thumbnail.calls == 1
    assert state.completed is not None
    assert state.completed[0] is None
    assert state.completed[1] is not None


@pytest.mark.anyio
async def test_runner_reuses_completed_thumbnail_for_playable_retry(tmp_path: Path) -> None:
    state = FakeState(
        make_context(playable_ready=False, thumbnail_ready=True),
    )
    source_probe = make_probe("mpeg4", "matroska,webm")
    output_probe = make_probe("hevc", "mov,mp4,m4a,3gp,3g2,mj2")
    inspector = FakeInspector([source_probe, output_probe])
    preparation = FakePreparationProcessor()
    playable = FakePlayableProcessor()
    thumbnail = FakeThumbnailProcessor()

    runner = make_runner(tmp_path, state, inspector, preparation, playable, thumbnail)

    await runner.run(state.context.job_id)

    assert state.process_calls == [
        (MediaTranscodingOperation.TRANSCODE, True, False),
    ]
    assert preparation.calls == []
    assert playable.operations == [PlayableMediaOperation.TRANSCODE]
    assert thumbnail.calls == 0
    assert state.completed is not None
    assert state.completed[0] is output_probe
    assert state.completed[1] is None


@pytest.mark.anyio
async def test_runner_ignores_stale_failed_job(tmp_path: Path) -> None:
    context = make_context()
    state = FakeState(
        MediaPreparationContext(
            job_id=context.job_id,
            asset_id=context.asset_id,
            source_path=context.source_path,
            source_metadata_updated_at=context.source_metadata_updated_at,
            status=MediaPreparationJobStatus.FAILED,
            operation=MediaTranscodingOperation.TRANSCODE,
            variant_id=context.variant_id,
            playable_ready=False,
            thumbnail_ready=False,
            duration_seconds=context.duration_seconds,
            source_is_current=True,
        ),
    )
    inspector = FakeInspector([])
    preparation = FakePreparationProcessor()
    playable = FakePlayableProcessor()
    thumbnail = FakeThumbnailProcessor()

    runner = make_runner(tmp_path, state, inspector, preparation, playable, thumbnail)

    await runner.run(state.context.job_id)

    assert state.failed_message is None
    assert state.completed is None
    assert inspector.paths == []
    assert preparation.calls == []
    assert playable.operations == []
    assert thumbnail.calls == 0


@pytest.mark.anyio
async def test_runner_rejects_stale_source(tmp_path: Path) -> None:
    state = FakeState(make_context(source_is_current=False))
    inspector = FakeInspector([])
    preparation = FakePreparationProcessor()
    playable = FakePlayableProcessor()
    thumbnail = FakeThumbnailProcessor()

    runner = make_runner(tmp_path, state, inspector, preparation, playable, thumbnail)

    with pytest.raises(RuntimeError, match="source changed after"):
        await runner.run(state.context.job_id)

    assert state.failed_message is not None
    assert inspector.paths == []
    assert preparation.calls == []
    assert playable.operations == []
    assert thumbnail.calls == 0
