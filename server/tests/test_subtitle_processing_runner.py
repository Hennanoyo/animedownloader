from pathlib import Path
from uuid import UUID, uuid7

import pytest
from animedownloader_media import FFmpegSubtitleProcessor
from animedownloader_media_asset import SubtitleTrackStatus
from animedownloader_storage import LocalStorage
from animedownloader_worker.subtitle_processing import (
    SubtitleProcessingContext,
    SubtitleProcessingRunner,
    SubtitleTrackContext,
)


class FakeState:
    def __init__(self, context: SubtitleProcessingContext) -> None:
        self.context = context
        self.transitions: list[tuple[str, UUID]] = []
        self.completed: list[tuple[UUID, str, str]] = []
        self.failed: list[tuple[UUID, str]] = []
        self.asset_completed = False

    async def load(self, asset_id: UUID) -> SubtitleProcessingContext:
        return self.context

    async def mark_processing(self, track_id: UUID) -> None:
        self.transitions.append(("processing", track_id))

    async def mark_completed(
        self,
        track_id: UUID,
        *,
        normalized_path: str,
        normalized_format: str,
    ) -> None:
        self.completed.append((track_id, normalized_path, normalized_format))

    async def mark_failed(self, track_id: UUID, *, error_message: str) -> None:
        self.failed.append((track_id, error_message))

    async def mark_asset_complete(self, asset_id: UUID) -> None:
        self.asset_completed = not self.failed


class StubProcessor(FFmpegSubtitleProcessor):
    def __init__(self, results: dict[UUID, str | Exception]) -> None:
        super().__init__()
        self.results = results
        self.calls: list[UUID] = []

    async def extract(
        self,
        *,
        media_path: Path,
        stream_index: int,
        codec_name: str | None,
        output_path: Path,
    ) -> str:
        track_id = UUID(output_path.stem)
        self.calls.append(track_id)
        result = self.results[track_id]
        if isinstance(result, Exception):
            raise result
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        return result

    async def normalize_external(
        self,
        *,
        source_path: Path,
        codec_name: str | None,
        output_path: Path,
    ) -> str:
        raise AssertionError("not used")


def make_context(
    *tracks: SubtitleTrackContext,
    ready: bool = False,
) -> SubtitleProcessingContext:
    return SubtitleProcessingContext(
        asset_id=uuid7(),
        media_path="/downloads/episode/episode.mkv",
        tracks=tracks,
        ready=ready,
    )


@pytest.mark.anyio
async def test_runner_processes_pending_tracks(tmp_path: Path) -> None:
    track_id = uuid7()
    context = make_context(
        SubtitleTrackContext(
            id=track_id,
            stream_index=2,
            codec_name="subrip",
            source_path=None,
            status=SubtitleTrackStatus.PENDING,
        ),
    )
    state = FakeState(context)
    processor = StubProcessor({track_id: "ass"})
    runner = SubtitleProcessingRunner(
        state=state,
        processor=processor,
        storage=LocalStorage(tmp_path / "storage", "http://localhost:8888"),
    )

    await runner.run(context.asset_id)

    assert state.transitions == [("processing", track_id)]
    assert processor.calls == [track_id]
    assert len(state.completed) == 1
    assert state.completed[0][2] == "ass"
    assert state.failed == []
    assert state.asset_completed


@pytest.mark.anyio
async def test_runner_keeps_failed_track_retryable(tmp_path: Path) -> None:
    track_id = uuid7()
    context = make_context(
        SubtitleTrackContext(
            id=track_id,
            stream_index=2,
            codec_name="subrip",
            source_path=None,
            status=SubtitleTrackStatus.FAILED,
        ),
    )
    state = FakeState(context)
    processor = StubProcessor({track_id: RuntimeError("convert failed")})
    runner = SubtitleProcessingRunner(
        state=state,
        processor=processor,
        storage=LocalStorage(tmp_path / "storage", "http://localhost:8888"),
    )

    await runner.run(context.asset_id)

    assert state.transitions == [("processing", track_id)]
    assert state.completed == []
    assert state.failed == [(track_id, "convert failed")]
    assert not state.asset_completed


@pytest.mark.anyio
async def test_runner_skips_ready_asset(tmp_path: Path) -> None:
    context = make_context(ready=True)
    state = FakeState(context)
    processor = StubProcessor({})
    runner = SubtitleProcessingRunner(
        state=state,
        processor=processor,
        storage=LocalStorage(tmp_path / "storage", "http://localhost:8888"),
    )

    await runner.run(context.asset_id)

    assert state.transitions == []
    assert state.asset_completed is False


@pytest.mark.anyio
async def test_runner_marks_empty_subtitle_set_complete(tmp_path: Path) -> None:
    context = make_context()
    state = FakeState(context)
    processor = StubProcessor({})
    runner = SubtitleProcessingRunner(
        state=state,
        processor=processor,
        storage=LocalStorage(tmp_path / "storage", "http://localhost:8888"),
    )

    await runner.run(context.asset_id)

    assert state.completed == []
    assert state.failed == []
    assert state.asset_completed


def test_context_status_is_explicit() -> None:
    track_id = uuid7()
    context = make_context(
        SubtitleTrackContext(
            id=track_id,
            stream_index=None,
            codec_name="ass",
            source_path=None,
            status=SubtitleTrackStatus.PENDING,
        ),
    )
    assert context.tracks[0].status is SubtitleTrackStatus.PENDING
