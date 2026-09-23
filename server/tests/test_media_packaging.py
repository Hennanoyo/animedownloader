from datetime import UTC, datetime
from uuid import uuid7

import pytest
from animedownloader_media_processing import MediaPackagingJob, MediaPackagingJobStatus
from animedownloader_media_processing.exceptions import InvalidMediaPackagingJobTransitionError


def make_job() -> MediaPackagingJob:
    return MediaPackagingJob(
        media_variant_id=uuid7(),
        package_id=uuid7(),
        source_path="/data/playable.mp4",
        source_variant_updated_at=datetime(2026, 9, 24, tzinfo=UTC),
        status=MediaPackagingJobStatus.PENDING.value,
    )


def test_media_packaging_job_tracks_attempts() -> None:
    job = make_job()
    job.transition_to(MediaPackagingJobStatus.PROCESSING)

    assert job.job_status is MediaPackagingJobStatus.PROCESSING
    assert job.attempt_count == 1
    assert job.started_at is not None

    job.transition_to(MediaPackagingJobStatus.COMPLETED)
    assert job.job_status is MediaPackagingJobStatus.COMPLETED
    assert job.completed_at is not None


def test_failed_packaging_job_cannot_be_reused_in_place() -> None:
    job = make_job()
    job.transition_to(MediaPackagingJobStatus.FAILED)

    with pytest.raises(
        InvalidMediaPackagingJobTransitionError,
        match="Invalid media packaging job transition",
    ):
        job.transition_to(MediaPackagingJobStatus.PENDING)
