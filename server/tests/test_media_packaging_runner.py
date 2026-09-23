from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid7

import pytest
from animedownloader_media import CMAFMediaSegment, CMAFPackagingResult
from animedownloader_media_processing import MediaPackagingJobStatus
from animedownloader_worker.media_packaging import (
    MediaPackagingContext,
    MediaPackagingRunner,
)


class FakeState:
    def __init__(self, context: MediaPackagingContext) -> None:
        self.context = context
        self.processing_calls = 0
        self.completed: tuple[Any, str] | None = None
        self.failed_message: str | None = None

    async def load(self, job_id: UUID) -> MediaPackagingContext:
        return self.context

    async def mark_processing(self, job_id: UUID) -> None:
        self.processing_calls += 1

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        representation: Any,
        package_root_key: str,
    ) -> None:
        self.completed = (representation, package_root_key)

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        self.failed_message = error_message


class FakeProcessor:
    async def process(
        self,
        *,
        media_path: Path,
        output_dir: Path,
    ) -> CMAFPackagingResult:
        return CMAFPackagingResult(
            playlist_path=output_dir / "index.m3u8",
            init_segment_path=output_dir / "init.mp4",
            segments=(
                CMAFMediaSegment(
                    number=0,
                    duration_seconds=2.0,
                    uri="s/00000.m4s",
                ),
            ),
        )


def make_context(
    *,
    source_is_current: bool = True,
) -> MediaPackagingContext:
    return MediaPackagingContext(
        job_id=uuid7(),
        package_id=uuid7(),
        variant_id=uuid7(),
        source_path="/data/playable.mp4",
        source_variant_updated_at=datetime(2026, 9, 24, tzinfo=UTC),
        status=MediaPackagingJobStatus.PENDING,
        width=1920,
        height=1080,
        size_bytes=1024,
        duration_seconds=2.0,
        video_codec="hevc",
        audio_codec="aac",
        source_is_current=source_is_current,
    )


@pytest.mark.anyio
async def test_runner_packages_current_playable_variant(tmp_path: Path) -> None:
    state = FakeState(make_context())

    await MediaPackagingRunner(
        state=state,
        processor=FakeProcessor(),
        media_root=tmp_path,
    ).run(state.context.job_id)

    assert state.processing_calls == 1
    assert state.completed is not None
    representation, package_root_key = state.completed
    assert representation.quality == "1080p"
    assert representation.segments[0].uri == "s/00000.m4s"
    assert package_root_key == f"streaming/{state.context.variant_id}"


@pytest.mark.anyio
async def test_runner_rejects_stale_playable_variant(tmp_path: Path) -> None:
    state = FakeState(make_context(source_is_current=False))

    with pytest.raises(RuntimeError, match="changed after"):
        await MediaPackagingRunner(
            state=state,
            processor=FakeProcessor(),
            media_root=tmp_path,
        ).run(state.context.job_id)

    assert state.failed_message is not None
