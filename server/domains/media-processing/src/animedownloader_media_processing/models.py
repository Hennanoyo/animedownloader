from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from animedownloader_anime import Episode
from animedownloader_database import Base
from animedownloader_download import DownloadJob
from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .enums import (
    MediaProcessingJobStatus,
    MediaPreparationJobStatus,
    MediaTranscodingOperation,
    MediaVariantKind,
    MediaVariantStatus,
)
from .exceptions import (
    InvalidMediaProcessingJobTransitionError,
    InvalidMediaPreparationJobTransitionError,
)


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

class MediaVariant(Base):
    __tablename__ = "media_variants"
    __table_args__ = (
        UniqueConstraint(
            "media_asset_id",
            "kind",
            name="uq_media_variants_asset_kind",
        ),
        Index("ix_media_variants_media_asset_id", "media_asset_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    media_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
    )
    kind: Mapped[str] = mapped_column(
        String(32),
        default=MediaVariantKind.PLAYABLE.value,
        server_default=MediaVariantKind.PLAYABLE.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=MediaVariantStatus.PENDING.value,
        server_default=MediaVariantStatus.PENDING.value,
    )
    source_path: Mapped[str | None] = mapped_column(String(2000))
    source_metadata_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    path: Mapped[str | None] = mapped_column(String(2000))
    format_name: Mapped[str | None] = mapped_column(String(128))
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    video_codec: Mapped[str | None] = mapped_column(String(64))
    audio_codec: Mapped[str | None] = mapped_column(String(64))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    frame_rate: Mapped[str | None] = mapped_column(String(32))
    error_message: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def variant_status(self) -> MediaVariantStatus:
        return MediaVariantStatus(self.status)

    @property
    def ready(self) -> bool:
        return self.variant_status is MediaVariantStatus.COMPLETED and self.path is not None

    def is_current(
        self,
        *,
        source_path: str,
        source_metadata_updated_at: datetime,
    ) -> bool:
        return (
            self.ready
            and self.source_path == source_path
            and self.source_metadata_updated_at == source_metadata_updated_at
        )

    def mark_processing(self) -> None:
        self.status = MediaVariantStatus.PROCESSING.value
        self.path = None
        self.error_message = None

    def mark_completed(
        self,
        *,
        source_path: str,
        source_metadata_updated_at: datetime,
        output_path: str,
        format_name: str | None,
        duration_seconds: float | None,
        size_bytes: int | None,
        video_codec: str | None,
        audio_codec: str | None,
        width: int | None,
        height: int | None,
        frame_rate: str | None,
    ) -> None:
        self.status = MediaVariantStatus.COMPLETED.value
        self.source_path = source_path
        self.source_metadata_updated_at = source_metadata_updated_at
        self.path = output_path
        self.format_name = format_name
        self.duration_seconds = duration_seconds
        self.size_bytes = size_bytes
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.width = width
        self.height = height
        self.frame_rate = frame_rate
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        self.status = MediaVariantStatus.FAILED.value
        self.path = None
        self.error_message = error_message[:2000]


class MediaPreparationJob(Base):
    __tablename__ = "media_preparation_jobs"
    __table_args__ = (
        Index("ix_media_preparation_jobs_media_asset_id", "media_asset_id"),
        Index("ix_media_preparation_jobs_variant_id", "variant_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    media_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
    )
    variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_variants.id", ondelete="CASCADE"),
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=MediaPreparationJobStatus.PENDING.value,
        server_default=MediaPreparationJobStatus.PENDING.value,
    )
    operation: Mapped[str | None] = mapped_column(String(32))
    source_path: Mapped[str] = mapped_column(String(2000))
    source_metadata_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    output_path: Mapped[str | None] = mapped_column(String(2000))
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

    @property
    def job_status(self) -> MediaPreparationJobStatus:
        return MediaPreparationJobStatus(self.status)

    @property
    def transcoding_operation(self) -> MediaTranscodingOperation | None:
        if self.operation is None:
            return None
        return MediaTranscodingOperation(self.operation)

    def transition_to(self, target: MediaPreparationJobStatus) -> None:
        current = self.job_status
        allowed: dict[
            MediaPreparationJobStatus,
            set[MediaPreparationJobStatus],
        ] = {
            MediaPreparationJobStatus.PENDING: {
                MediaPreparationJobStatus.PROCESSING,
                MediaPreparationJobStatus.FAILED,
            },
            MediaPreparationJobStatus.PROCESSING: {
                MediaPreparationJobStatus.COMPLETED,
                MediaPreparationJobStatus.FAILED,
            },
            MediaPreparationJobStatus.COMPLETED: set(),
            MediaPreparationJobStatus.FAILED: set(),
        }

        if target is current:
            return
        if target not in allowed[current]:
            raise InvalidMediaPreparationJobTransitionError(current, target)

        now = datetime.now(UTC)
        self.status = target.value

        if target is MediaPreparationJobStatus.PROCESSING:
            self.attempt_count += 1
            if self.started_at is None:
                self.started_at = now
            self.error_message = None

        if target is MediaPreparationJobStatus.COMPLETED:
            self.completed_at = now
            self.error_message = None

        if target is MediaPreparationJobStatus.FAILED:
            self.error_message = "Media preparation failed."
