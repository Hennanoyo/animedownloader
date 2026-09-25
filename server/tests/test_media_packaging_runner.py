from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid7

import pytest
from animedownloader_config import JobProgressEvent
from animedownloader_media import CMAFMediaSegment, CMAFPackagingResult
from animedownloader_media_processing import MediaPackagingJobStatus
from animedownloader_storage import LocalStorage, StreamingPackageArtifact
from animedownloader_worker.media_packaging import (
    MediaPackagingContext,
    MediaPackagingRunner,
)


class FakeState:
    def __init__(self, context: MediaPackagingContext) -> None:
        self.context = context
        self.processing_calls = 0
        self.completed: tuple[Any, StreamingPackageArtifact] | None = None
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
        package_artifact: StreamingPackageArtifact,
    ) -> None:
        self.completed = (representation, package_artifact)

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        self.failed_message = error_message


class FakeProcessor:
    async def process(
        self,
        *,
        media_path: Path,
        output_dir: Path,
        duration_seconds: float | None = None,
        on_progress=None,
    ) -> CMAFPackagingResult:
        del media_path, duration_seconds
        if on_progress is not None:
            await on_progress(25.0)
            await on_progress(60.0)
        segment_path = output_dir / "s" / "00000.m4s"
        segment_path.parent.mkdir(parents=True, exist_ok=True)
        segment_path.write_bytes(b"segment")
        playlist_path = output_dir / "index.m3u8"
        playlist_path.write_text("#EXTM3U\n", encoding="utf-8")
        init_path = output_dir / "init.mp4"
        init_path.write_bytes(
            bytes.fromhex(
                "0000001568766343"
                "010220000000"
                "000000000000"
                "78",
            ),
        )
        return CMAFPackagingResult(
            playlist_path=playlist_path,
            init_segment_path=init_path,
            segments=(
                CMAFMediaSegment(
                    number=0,
                    duration_seconds=2.0,
                    uri="s/00000.m4s",
                ),
            ),
            video_codec_string="hvc1.2.4.L120",
        )


def make_context(
    *,
    source_is_current: bool = True,
) -> MediaPackagingContext:
    return MediaPackagingContext(
        job_id=uuid7(),
        package_id=uuid7(),
        variant_id=uuid7(),
        source_path="playable/source.mp4",
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
    storage = LocalStorage(tmp_path / "storage", "http://localhost:8888")
    source = tmp_path / "storage" / "playable" / "source.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"playable")

    events: list[tuple[str, float | None, str | None]] = []

    async def on_progress(event: JobProgressEvent) -> None:
        events.append((event.status, event.progress_percent, event.stage))

    await MediaPackagingRunner(
        state=state,
        processor=FakeProcessor(),
        storage=storage,
        on_progress=on_progress,
    ).run(state.context.job_id)

    assert state.processing_calls == 1
    assert events == [
        ("processing", 0, "streaming"),
        ("processing", 25.0, "streaming"),
        ("processing", 60.0, "streaming"),
        ("completed", 100, "streaming"),
    ]
    assert state.completed is not None
    representation, package_artifact = state.completed
    assert representation.quality == "1080p"
    assert representation.segments[0].uri == "s/00000.m4s"
    assert package_artifact.object_prefix == f"streaming/{state.context.package_id}"
    assert (
        package_artifact.master_playlist_key == f"streaming/{state.context.package_id}/master.m3u8"
    )
    assert (
        package_artifact.dash_manifest_key == f"streaming/{state.context.package_id}/manifest.mpd"
    )
    assert package_artifact.representation_key("1080p", "index.m3u8") == (
        f"streaming/{state.context.package_id}/1080p/index.m3u8"
    )


@pytest.mark.anyio
async def test_runner_rejects_stale_playable_variant(tmp_path: Path) -> None:
    state = FakeState(make_context(source_is_current=False))

    with pytest.raises(RuntimeError, match="changed after"):
        await MediaPackagingRunner(
            state=state,
            processor=FakeProcessor(),
            storage=LocalStorage(tmp_path / "storage", "http://localhost:8888"),
        ).run(state.context.job_id)

    assert state.failed_message is not None
