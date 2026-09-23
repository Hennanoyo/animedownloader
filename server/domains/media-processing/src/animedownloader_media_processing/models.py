from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from animedownloader_anime import Episode
from animedownloader_database import Base
from animedownloader_download import DownloadJob
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .enums import MediaProcessingJobStatus
from .exceptions import InvalidMediaProcessingJobTransitionError


class MediaProcessingJob(Base):
    __tablename__ = "media_processing_jobs"
    __table_args__ = (
        UniqueConstraint(
            "download_job_id",
            name="uq_media_processing_jobs_download_job",
        ),
        Index("ix_media_processing_jobs_episode_id", "episode_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    episode_id: Mapped[UUID] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"),
        index=False,
    )
    download_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("download_jobs.id", ondelete="SET NULL"),
    )
    download_directory: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(32),
        default=MediaProcessingJobStatus.PENDING.value,
        server_default=MediaProcessingJobStatus.PENDING.value,
    )
    media_path: Mapped[str | None] = mapped_column(String(2000))
    probe_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON)
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    error_message: Mapped[str | None] = mapped_column(String(2000))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    episode: Mapped[Episode] = relationship()
    download_job: Mapped[DownloadJob | None] = relationship()

    @property
    def job_status(self) -> MediaProcessingJobStatus:
        return MediaProcessingJobStatus(self.status)

    def transition_to(self, target: MediaProcessingJobStatus) -> None:
        current = self.job_status
        allowed: dict[
            MediaProcessingJobStatus,
            set[MediaProcessingJobStatus],
        ] = {
            MediaProcessingJobStatus.PENDING: {
                MediaProcessingJobStatus.PROCESSING,
                MediaProcessingJobStatus.FAILED,
            },
            MediaProcessingJobStatus.PROCESSING: {
                MediaProcessingJobStatus.COMPLETED,
                MediaProcessingJobStatus.FAILED,
            },
            MediaProcessingJobStatus.COMPLETED: set(),
            MediaProcessingJobStatus.FAILED: {
                MediaProcessingJobStatus.PENDING,
            },
        }

        if target is current:
            return
        if target not in allowed[current]:
            raise InvalidMediaProcessingJobTransitionError(current, target)

        now = datetime.now(UTC)
        self.status = target.value

        if target is MediaProcessingJobStatus.PROCESSING:
            self.attempt_count += 1
            if self.started_at is None:
                self.started_at = now
            self.error_message = None

        if target is MediaProcessingJobStatus.COMPLETED:
            self.completed_at = now
            self.error_message = None

        if target is MediaProcessingJobStatus.FAILED:
            self.error_message = "Media processing failed."

        if target is MediaProcessingJobStatus.PENDING:
            self.media_path = None
            self.probe_metadata = None
            self.completed_at = None
