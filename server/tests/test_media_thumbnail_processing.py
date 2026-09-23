from pathlib import Path
from uuid import UUID, uuid7

import pytest
from animedownloader_media import (
    FFmpegThumbnailSpriteProcessor,
    ThumbnailSpriteResult,
)
from animedownloader_media_asset import MediaThumbnailStatus
from animedownloader_worker.media_thumbnail_processing import (
    MediaThumbnailProcessingContext,
    MediaThumbnailProcessingRunner,
)


class FakeState:
    def __init__(self, context: MediaThumbnailProcessingContext) -> None:
        self.context = context
        self.processing = 0
        self.completed: tuple[str, str] | None = None
        self.failed: str | None = None

    async def load(self, asset_id: UUID) -> MediaThumbnailProcessingContext:
        return self.context

    async def mark_processing(self, asset_id: UUID) -> None:
        self.processing += 1

    async def mark_completed(
        self,
        asset_id: UUID,
        *,
        result: ThumbnailSpriteResult,
    ) -> None:
        self.completed = (str(result.sprite_path), str(result.vtt_path))

    async def mark_failed(self, asset_id: UUID, *, error_message: str) -> None:
        self.failed = error_message


class StubProcessor(FFmpegThumbnailSpriteProcessor):
    async def generate(
        self,
        *,
        media_path: Path,
        output_dir: Path,
        duration_seconds: float | None,
    ) -> ThumbnailSpriteResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        sprite_path = output_dir / "sprite.jpg"
        vtt_path = output_dir / "sprite.vtt"
        sprite_path.write_bytes(b"sprite")
        vtt_path.write_text("WEBVTT\n", encoding="utf-8")
        return ThumbnailSpriteResult(
            sprite_path=sprite_path,
            vtt_path=vtt_path,
            frame_count=3,
            interval_seconds=5.0,
        )


class FailingProcessor(FFmpegThumbnailSpriteProcessor):
    async def generate(
        self,
        *,
        media_path: Path,
        output_dir: Path,
        duration_seconds: float | None,
    ) -> ThumbnailSpriteResult:
        raise RuntimeError("thumbnail generation failed")


def make_context(
    status: MediaThumbnailStatus = MediaThumbnailStatus.PENDING,
    ready: bool = False,
) -> MediaThumbnailProcessingContext:
    return MediaThumbnailProcessingContext(
        asset_id=uuid7(),
        media_path="/downloads/episode/episode.mkv",
        duration_seconds=60.0,
        status=status,
        ready=ready,
    )


@pytest.mark.anyio
async def test_runner_marks_thumbnail_completed(tmp_path: Path) -> None:
    context = make_context()
    state = FakeState(context)
    runner = MediaThumbnailProcessingRunner(
        state=state,
        processor=StubProcessor(),
        media_root=tmp_path,
    )

    await runner.run(context.asset_id)

    assert state.processing == 1
    assert state.failed is None
    assert state.completed is not None
    assert Path(state.completed[0]).read_bytes() == b"sprite"
    assert Path(state.completed[1]).read_text(encoding="utf-8") == "WEBVTT\n"


@pytest.mark.anyio
async def test_runner_persists_failure_without_raising(tmp_path: Path) -> None:
    context = make_context()
    state = FakeState(context)
    runner = MediaThumbnailProcessingRunner(
        state=state,
        processor=FailingProcessor(),
        media_root=tmp_path,
    )

    await runner.run(context.asset_id)

    assert state.processing == 1
    assert state.completed is None
    assert state.failed == "thumbnail generation failed"


@pytest.mark.anyio
async def test_runner_skips_ready_thumbnail(tmp_path: Path) -> None:
    context = make_context(
        status=MediaThumbnailStatus.COMPLETED,
        ready=True,
    )
    state = FakeState(context)
    runner = MediaThumbnailProcessingRunner(
        state=state,
        processor=FailingProcessor(),
        media_root=tmp_path,
    )

    await runner.run(context.asset_id)

    assert state.processing == 0
    assert state.failed is None
    assert state.completed is None
