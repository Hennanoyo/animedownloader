from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from animedownloader_database import Base
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .enums import SubtitleTrackStatus
from .metadata import MediaAssetMetadata, SubtitleTrackMetadata


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        UniqueConstraint("episode_id", name="uq_media_assets_episode"),
        UniqueConstraint(
            "processing_job_id",
            name="uq_media_assets_processing_job",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    episode_id: Mapped[UUID] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"),
        index=True,
    )
    processing_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media_processing_jobs.id", ondelete="SET NULL"),
    )
    path: Mapped[str] = mapped_column(String(2000))
    format_name: Mapped[str | None] = mapped_column(String(128))
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    video_codec: Mapped[str | None] = mapped_column(String(64))
    audio_codec: Mapped[str | None] = mapped_column(String(64))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    frame_rate: Mapped[str | None] = mapped_column(String(32))
    metadata_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    subtitle_tracks_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    subtitle_tracks_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    subtitle_tracks: Mapped[list[SubtitleTrack]] = relationship(
        back_populates="media_asset",
        cascade="all, delete-orphan",
        order_by="SubtitleTrack.stream_index",
    )

    @property
    def metadata_ready(self) -> bool:
        return self.metadata_updated_at is not None

    @property
    def subtitle_tracks_ready(self) -> bool:
        return self.subtitle_tracks_updated_at is not None

    @property
    def subtitle_processing_ready(self) -> bool:
        if self.subtitle_tracks_processed_at is None:
            return False
        return all(
            track.status == SubtitleTrackStatus.COMPLETED.value
            for track in self.subtitle_tracks
        )

    def update_metadata(self, metadata: MediaAssetMetadata) -> None:
        self.format_name = metadata.format_name
        self.duration_seconds = metadata.duration_seconds
        self.size_bytes = metadata.size_bytes
        self.video_codec = metadata.video_codec
        self.audio_codec = metadata.audio_codec
        self.width = metadata.width
        self.height = metadata.height
        self.frame_rate = metadata.frame_rate
        self.metadata_updated_at = datetime.now(UTC)

    def update_subtitle_tracks(
        self,
        tracks: tuple[SubtitleTrackMetadata, ...],
    ) -> None:
        self.subtitle_tracks = [
            SubtitleTrack(
                stream_index=track.stream_index,
                language=track.language,
                title=track.title,
                codec_name=track.codec_name,
                source_path=track.source_path,
                is_default=track.is_default,
                is_forced=track.is_forced,
            )
            for track in tracks
        ]
        self.subtitle_tracks_updated_at = datetime.now(UTC)
        self.subtitle_tracks_processed_at = None

    def mark_subtitle_processing_complete(self) -> None:
        if not all(
            track.status == SubtitleTrackStatus.COMPLETED.value
            for track in self.subtitle_tracks
        ):
            return
        self.subtitle_tracks_processed_at = datetime.now(UTC)


class SubtitleTrack(Base):
    __tablename__ = "subtitle_tracks"
    __table_args__ = (
        UniqueConstraint(
            "media_asset_id",
            "stream_index",
            name="uq_subtitle_tracks_asset_stream",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    media_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        index=True,
    )
    stream_index: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(32))
    title: Mapped[str | None] = mapped_column(String(500))
    codec_name: Mapped[str | None] = mapped_column(String(64))
    source_path: Mapped[str | None] = mapped_column(String(2000))
    normalized_path: Mapped[str | None] = mapped_column(String(2000))
    normalized_format: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        String(32),
        default=SubtitleTrackStatus.PENDING.value,
        server_default=SubtitleTrackStatus.PENDING.value,
    )
    error_message: Mapped[str | None] = mapped_column(String(2000))
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    is_forced: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    media_asset: Mapped[MediaAsset] = relationship(
        back_populates="subtitle_tracks",
    )

    @property
    def processing_status(self) -> SubtitleTrackStatus:
        return SubtitleTrackStatus(self.status)

    def mark_processing(self) -> None:
        self.status = SubtitleTrackStatus.PROCESSING.value
        self.error_message = None

    def mark_completed(
        self,
        *,
        normalized_path: str,
        normalized_format: str,
    ) -> None:
        self.status = SubtitleTrackStatus.COMPLETED.value
        self.normalized_path = normalized_path
        self.normalized_format = normalized_format
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        self.status = SubtitleTrackStatus.FAILED.value
        self.error_message = error_message[:2000]

    def retry(self) -> None:
        self.status = SubtitleTrackStatus.PENDING.value
        self.normalized_path = None
        self.normalized_format = None
        self.error_message = None
