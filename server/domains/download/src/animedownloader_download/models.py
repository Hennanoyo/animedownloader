from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from animedownloader_anime import Episode
from animedownloader_database import Base
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .enums import DownloadJobStatus
from .exceptions import InvalidDownloadJobTransitionError


class DownloadJob(Base):
    __tablename__ = "download_jobs"
    __table_args__ = (
        CheckConstraint(
            "downloaded_bytes >= 0",
            name="ck_download_jobs_downloaded_bytes_nonnegative",
        ),
        CheckConstraint(
            "total_bytes IS NULL OR total_bytes >= 0",
            name="ck_download_jobs_total_bytes_nonnegative",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_download_jobs_attempt_count_nonnegative",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    episode_id: Mapped[UUID] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=DownloadJobStatus.PENDING.value,
        server_default=DownloadJobStatus.PENDING.value,
    )
    downloaded_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default="0",
    )
    total_bytes: Mapped[int | None] = mapped_column(BigInteger)
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

    @property
    def job_status(self) -> DownloadJobStatus:
        return DownloadJobStatus(self.status)

    def transition_to(
        self,
        target: DownloadJobStatus,
        *,
        error_message: str | None = None,
        downloaded_bytes: int | None = None,
        total_bytes: int | None = None,
    ) -> None:
        current = self.job_status
        allowed: dict[DownloadJobStatus, set[DownloadJobStatus]] = {
            DownloadJobStatus.PENDING: {
                DownloadJobStatus.DOWNLOADING,
                DownloadJobStatus.FAILED,
                DownloadJobStatus.CANCELLED,
            },
            DownloadJobStatus.DOWNLOADING: {
                DownloadJobStatus.PAUSED,
                DownloadJobStatus.COMPLETED,
                DownloadJobStatus.FAILED,
                DownloadJobStatus.CANCELLED,
            },
            DownloadJobStatus.PAUSED: {
                DownloadJobStatus.DOWNLOADING,
                DownloadJobStatus.CANCELLED,
            },
            DownloadJobStatus.COMPLETED: set(),
            DownloadJobStatus.FAILED: set(),
            DownloadJobStatus.CANCELLED: set(),
        }

        if target is current:
            if downloaded_bytes is not None:
                self.downloaded_bytes = downloaded_bytes
            if total_bytes is not None:
                self.total_bytes = total_bytes
            if target is DownloadJobStatus.FAILED and error_message:
                self.error_message = error_message
            return

        if target not in allowed[current]:
            raise InvalidDownloadJobTransitionError(current, target)

        now = datetime.now(UTC)
        self.status = target.value

        if downloaded_bytes is not None:
            self.downloaded_bytes = downloaded_bytes
        if total_bytes is not None:
            self.total_bytes = total_bytes

        if target is DownloadJobStatus.DOWNLOADING:
            if current is DownloadJobStatus.PENDING:
                self.started_at = now
                self.attempt_count += 1
            self.error_message = None

        if target is DownloadJobStatus.FAILED:
            self.error_message = error_message or "Download failed."

        if target is DownloadJobStatus.COMPLETED:
            self.completed_at = now
            self.error_message = None

        if target is DownloadJobStatus.CANCELLED:
            self.completed_at = now
