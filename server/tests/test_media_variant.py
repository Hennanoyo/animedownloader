from datetime import UTC, datetime
from uuid import uuid7

import pytest
from animedownloader_media_processing import (
    MediaTranscodingJob,
    MediaTranscodingJobStatus,
    MediaTranscodingOperation,
    MediaVariant,
    MediaVariantKind,
    MediaVariantStatus,
)
from animedownloader_media_processing.exceptions import (
    InvalidMediaTranscodingJobTransitionError,
)


def test_media_variant_tracks_current_source() -> None:
    now = datetime(2026, 9, 24, tzinfo=UTC)
    asset_id = uuid7()
    variant = MediaVariant(
        media_asset_id=asset_id,
        kind=MediaVariantKind.PLAYABLE.value,
    )

    assert variant.variant_status is MediaVariantStatus.PENDING
    assert not variant.ready

    variant.mark_processing()
    assert variant.variant_status is MediaVariantStatus.PROCESSING
    assert variant.path is None

    variant.mark_completed(
        source_path="/downloads/source.mkv",
        source_metadata_updated_at=now,
        output_path="/data/media/playable/asset.mp4",
        format_name="mov,mp4,m4a,3gp,3g2,mj2",
        duration_seconds=60.0,
        size_bytes=1024,
        video_codec="hevc",
        audio_codec="aac",
        width=1920,
        height=1080,
        frame_rate="24/1",
    )

    assert variant.ready
    assert variant.is_current(
        source_path="/downloads/source.mkv",
        source_metadata_updated_at=now,
    )
    assert not variant.is_current(
        source_path="/downloads/other.mkv",
        source_metadata_updated_at=now,
    )


def test_media_variant_failure_clears_output() -> None:
    variant = MediaVariant(
        media_asset_id=uuid7(),
        kind=MediaVariantKind.PLAYABLE.value,
    )
    variant.mark_failed("encoder failed")

    assert variant.variant_status is MediaVariantStatus.FAILED
    assert variant.path is None
    assert variant.error_message == "encoder failed"


def test_media_transcoding_job_tracks_operation_and_attempts() -> None:
    job = MediaTranscodingJob(
        media_asset_id=uuid7(),
        variant_id=uuid7(),
        source_path="/downloads/source.mkv",
        source_metadata_updated_at=datetime(2026, 9, 24, tzinfo=UTC),
    )

    assert job.job_status is MediaTranscodingJobStatus.PENDING
    assert job.transcoding_operation is None

    job.operation = MediaTranscodingOperation.TRANSCODE.value
    job.transition_to(MediaTranscodingJobStatus.PROCESSING)

    assert job.job_status is MediaTranscodingJobStatus.PROCESSING
    assert job.transcoding_operation is MediaTranscodingOperation.TRANSCODE
    assert job.attempt_count == 1
    assert job.started_at is not None

    job.transition_to(MediaTranscodingJobStatus.COMPLETED)
    assert job.job_status is MediaTranscodingJobStatus.COMPLETED
    assert job.completed_at is not None


def test_failed_transcoding_job_cannot_be_reused_in_place() -> None:
    job = MediaTranscodingJob(
        media_asset_id=uuid7(),
        variant_id=uuid7(),
        source_path="/downloads/source.mkv",
        source_metadata_updated_at=datetime(2026, 9, 24, tzinfo=UTC),
        status=MediaTranscodingJobStatus.FAILED.value,
    )

    with pytest.raises(InvalidMediaTranscodingJobTransitionError):
        job.transition_to(MediaTranscodingJobStatus.PENDING)