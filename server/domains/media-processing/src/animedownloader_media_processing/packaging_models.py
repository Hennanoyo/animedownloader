from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from animedownloader_database import Base
from sqlalchemy import (
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
    MediaPackagingJobStatus,
    MediaStreamingPackageStatus,
    MediaStreamingRepresentationStatus,
)
from .exceptions import InvalidMediaPackagingJobTransitionError


class MediaStreamingPackage(Base):
    __tablename__ = "media_streaming_packages"
    __table_args__ = (
        Index("ix_media_streaming_packages_media_variant_id", "media_variant_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    media_variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_variants.id", ondelete="CASCADE"),
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=MediaStreamingPackageStatus.PENDING.value,
        server_default=MediaStreamingPackageStatus.PENDING.value,
    )
    source_path: Mapped[str] = mapped_column(String(2000))
    source_variant_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    hls_master_key: Mapped[str | None] = mapped_column(String(2000))
    dash_manifest_key: Mapped[str | None] = mapped_column(String(2000))
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

    representations: Mapped[list[MediaStreamingRepresentation]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
    )

    @property
    def package_status(self) -> MediaStreamingPackageStatus:
        return MediaStreamingPackageStatus(self.status)

    def is_current(
        self,
        *,
        source_path: str,
        source_variant_updated_at: datetime,
    ) -> bool:
        return (
            self.package_status is MediaStreamingPackageStatus.COMPLETED
            and self.source_path == source_path
            and self.source_variant_updated_at == source_variant_updated_at
            and self.hls_master_key is not None
            and self.dash_manifest_key is not None
        )


class MediaStreamingRepresentation(Base):
    __tablename__ = "media_streaming_representations"
    __table_args__ = (
        Index(
            "ix_media_streaming_representations_package_id",
            "package_id",
        ),
        UniqueConstraint(
            "package_id",
            "quality",
            name="uq_media_streaming_representations_package_quality",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    package_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_streaming_packages.id", ondelete="CASCADE"),
    )
    quality: Mapped[str] = mapped_column(String(32))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    bandwidth: Mapped[int] = mapped_column(BigInteger)
    video_codec: Mapped[str] = mapped_column(String(64))
    audio_codec: Mapped[str | None] = mapped_column(String(64))
    duration_seconds: Mapped[float] = mapped_column(Float)
    hls_playlist_key: Mapped[str] = mapped_column(String(2000))
    init_segment_key: Mapped[str] = mapped_column(String(2000))
    segment_directory_key: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(
        String(32),
        default=MediaStreamingRepresentationStatus.PENDING.value,
        server_default=MediaStreamingRepresentationStatus.PENDING.value,
    )
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

    package: Mapped[MediaStreamingPackage] = relationship(
        back_populates="representations",
    )

    @property
    def representation_status(self) -> MediaStreamingRepresentationStatus:
        return MediaStreamingRepresentationStatus(self.status)


class MediaPackagingJob(Base):
    __tablename__ = "media_packaging_jobs"
    __table_args__ = (
        Index("ix_media_packaging_jobs_media_variant_id", "media_variant_id"),
        Index("ix_media_packaging_jobs_package_id", "package_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    media_variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_variants.id", ondelete="CASCADE"),
    )
    package_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_streaming_packages.id", ondelete="CASCADE"),
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=MediaPackagingJobStatus.PENDING.value,
        server_default=MediaPackagingJobStatus.PENDING.value,
    )
    source_path: Mapped[str] = mapped_column(String(2000))
    source_variant_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
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
    def job_status(self) -> MediaPackagingJobStatus:
        return MediaPackagingJobStatus(self.status)

    def transition_to(self, target: MediaPackagingJobStatus) -> None:
        current = self.job_status
        allowed: dict[
            MediaPackagingJobStatus,
            set[MediaPackagingJobStatus],
        ] = {
            MediaPackagingJobStatus.PENDING: {
                MediaPackagingJobStatus.PROCESSING,
                MediaPackagingJobStatus.FAILED,
            },
            MediaPackagingJobStatus.PROCESSING: {
                MediaPackagingJobStatus.COMPLETED,
                MediaPackagingJobStatus.FAILED,
            },
            MediaPackagingJobStatus.COMPLETED: set(),
            MediaPackagingJobStatus.FAILED: set(),
        }

        if target is current:
            return
        if target not in allowed[current]:
            raise InvalidMediaPackagingJobTransitionError(
                current.value,
                target.value,
            )

        now = datetime.now(UTC)
        self.status = target.value

        if target is MediaPackagingJobStatus.PROCESSING:
            self.attempt_count += 1
            if self.started_at is None:
                self.started_at = now
            self.error_message = None

        if target is MediaPackagingJobStatus.COMPLETED:
            self.completed_at = now
            self.error_message = None

        if target is MediaPackagingJobStatus.FAILED:
            self.error_message = "Media packaging failed."
