from datetime import UTC, datetime
from uuid import uuid7

import pytest
from animedownloader_media_processing import (
    InvalidMediaProcessingJobTransitionError,
    MediaProcessingJob,
    MediaProcessingJobStatus,
)


def make_job(
    status: MediaProcessingJobStatus = MediaProcessingJobStatus.PENDING,
) -> MediaProcessingJob:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    return MediaProcessingJob(
        id=uuid7(),
        episode_id=uuid7(),
        download_job_id=uuid7(),
        download_directory=str(uuid7()),
        status=status.value,
        media_path=None,
        probe_metadata=None,
        attempt_count=0,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )


def test_media_processing_job_lifecycle() -> None:
    job = make_job()

    job.transition_to(MediaProcessingJobStatus.PROCESSING)
    assert job.job_status is MediaProcessingJobStatus.PROCESSING
    assert job.attempt_count == 1
    assert job.started_at is not None

    job.probe_metadata = {"format": {"format_name": "matroska"}}
    job.media_path = "/downloads/job/episode.mkv"
    job.transition_to(MediaProcessingJobStatus.COMPLETED)

    assert job.job_status is MediaProcessingJobStatus.COMPLETED
    assert job.completed_at is not None
    assert job.error_message is None


def test_failed_job_can_be_retried() -> None:
    job = make_job()
    job.transition_to(MediaProcessingJobStatus.PROCESSING)
    job.transition_to(MediaProcessingJobStatus.FAILED)

    assert job.job_status is MediaProcessingJobStatus.FAILED
    assert job.attempt_count == 1

    job.transition_to(MediaProcessingJobStatus.PENDING)
    assert job.job_status is MediaProcessingJobStatus.PENDING
    assert job.probe_metadata is None
    assert job.media_path is None

    job.transition_to(MediaProcessingJobStatus.PROCESSING)
    assert job.attempt_count == 2


def test_completed_job_cannot_transition() -> None:
    job = make_job(MediaProcessingJobStatus.COMPLETED)

    with pytest.raises(InvalidMediaProcessingJobTransitionError):
        job.transition_to(MediaProcessingJobStatus.PROCESSING)
