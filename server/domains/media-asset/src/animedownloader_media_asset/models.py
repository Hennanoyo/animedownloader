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

from .enums import MediaAttachmentStatus, MediaThumbnailStatus, SubtitleTrackStatus
from .metadata import (
    MediaAssetMetadata,
    MediaAttachmentMetadata,
    MediaChapterMetadata,
    SubtitleTrackMetadata,
)


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
    chapters_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    attachments_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    attachments_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    thumbnail_status: Mapped[str] = mapped_column(
        String(32),
        default=MediaThumbnailStatus.PENDING.value,
        server_default=MediaThumbnailStatus.PENDING.value,
    )
    thumbnail_sprite_path: Mapped[str | None] = mapped_column(String(2000))
    thumbnail_vtt_path: Mapped[str | None] = mapped_column(String(2000))
    thumbnail_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    thumbnail_error_message: Mapped[str | None] = mapped_column(String(2000))
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
    chapters: Mapped[list[MediaChapter]] = relationship(
        back_populates="media_asset",
        cascade="all, delete-orphan",
        order_by="MediaChapter.chapter_index",
    )
    attachments: Mapped[list[MediaAttachment]] = relationship(
        back_populates="media_asset",
        cascade="all, delete-orphan",
        order_by="MediaAttachment.attachment_index",
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
            track.status == SubtitleTrackStatus.COMPLETED.value for track in self.subtitle_tracks
        )

    @property
    def chapters_ready(self) -> bool:
        return self.chapters_updated_at is not None

    @property
    def attachments_ready(self) -> bool:
        return self.attachments_updated_at is not None

    @property
    def attachment_processing_ready(self) -> bool:
        if self.attachments_processed_at is None:
            return False
        return all(
            attachment.status == MediaAttachmentStatus.COMPLETED.value
            for attachment in self.attachments
        )

    @property
    def thumbnail_processing_status(self) -> MediaThumbnailStatus:
        return MediaThumbnailStatus(self.thumbnail_status)

    @property
    def thumbnail_ready(self) -> bool:
        return (
            self.thumbnail_processing_status is MediaThumbnailStatus.COMPLETED
            and self.thumbnail_sprite_path is not None
            and self.thumbnail_vtt_path is not None
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
        self.retry_thumbnail()

    def update_subtitle_tracks(
        self,
        tracks: tuple[SubtitleTrackMetadata, ...],
    ) -> None:
        existing = {track.stream_index: track for track in self.subtitle_tracks}
        incoming = {track.stream_index for track in tracks}
        self.subtitle_tracks = [
            track for track in self.subtitle_tracks if track.stream_index in incoming
        ]

        for track in tracks:
            current = existing.get(track.stream_index)
            if current is None:
                current = SubtitleTrack(stream_index=track.stream_index)
                self.subtitle_tracks.append(current)

            current.language = track.language
            current.title = track.title
            current.codec_name = track.codec_name
            current.source_path = track.source_path
            current.is_default = track.is_default
            current.is_forced = track.is_forced
            current.status = SubtitleTrackStatus.PENDING.value
            current.normalized_path = None
            current.normalized_format = None
            current.error_message = None

        self.subtitle_tracks_updated_at = datetime.now(UTC)
        self.subtitle_tracks_processed_at = None

    def update_chapters(
        self,
        chapters: tuple[MediaChapterMetadata, ...],
    ) -> None:
        existing = {chapter.chapter_index: chapter for chapter in self.chapters}
        incoming = {chapter.chapter_index for chapter in chapters}
        self.chapters = [chapter for chapter in self.chapters if chapter.chapter_index in incoming]

        for chapter in chapters:
            current = existing.get(chapter.chapter_index)
            if current is None:
                current = MediaChapter(chapter_index=chapter.chapter_index)
                self.chapters.append(current)

            current.chapter_id = chapter.id
            current.start_time_seconds = chapter.start_time_seconds
            current.end_time_seconds = chapter.end_time_seconds
            current.title = chapter.title

        self.chapters_updated_at = datetime.now(UTC)

    def update_attachments(
        self,
        attachments: tuple[MediaAttachmentMetadata, ...],
    ) -> None:
        existing = {attachment.attachment_index: attachment for attachment in self.attachments}
        incoming = {attachment.attachment_index for attachment in attachments}
        self.attachments = [
            attachment for attachment in self.attachments if attachment.attachment_index in incoming
        ]

        for attachment in attachments:
            current = existing.get(attachment.attachment_index)
            if current is None:
                current = MediaAttachment(
                    attachment_index=attachment.attachment_index,
                    stream_index=attachment.stream_index,
                )
                self.attachments.append(current)

            current.stream_index = attachment.stream_index
            current.filename = attachment.filename
            current.mime_type = attachment.mime_type
            current.description = attachment.description
            current.is_font = attachment.is_font
            current.status = MediaAttachmentStatus.PENDING.value
            current.extracted_path = None
            current.size_bytes = None
            current.font_id = None
            current.error_message = None

        self.attachments_updated_at = datetime.now(UTC)
        self.attachments_processed_at = None

    def mark_subtitle_processing_complete(self) -> None:
        if not all(
            track.status == SubtitleTrackStatus.COMPLETED.value for track in self.subtitle_tracks
        ):
            return
        self.subtitle_tracks_processed_at = datetime.now(UTC)

    def mark_attachment_processing_complete(self) -> None:
        if not all(
            attachment.status == MediaAttachmentStatus.COMPLETED.value
            for attachment in self.attachments
        ):
            return
        self.attachments_processed_at = datetime.now(UTC)

    def mark_thumbnail_processing(self) -> None:
        self.thumbnail_status = MediaThumbnailStatus.PROCESSING.value
        self.thumbnail_sprite_path = None
        self.thumbnail_vtt_path = None
        self.thumbnail_updated_at = None
        self.thumbnail_error_message = None

    def mark_thumbnail_completed(
        self,
        *,
        sprite_path: str,
        vtt_path: str,
    ) -> None:
        self.thumbnail_status = MediaThumbnailStatus.COMPLETED.value
        self.thumbnail_sprite_path = sprite_path
        self.thumbnail_vtt_path = vtt_path
        self.thumbnail_updated_at = datetime.now(UTC)
        self.thumbnail_error_message = None

    def mark_thumbnail_failed(self, error_message: str) -> None:
        self.thumbnail_status = MediaThumbnailStatus.FAILED.value
        self.thumbnail_error_message = error_message[:2000]

    def retry_thumbnail(self) -> None:
        self.thumbnail_status = MediaThumbnailStatus.PENDING.value
        self.thumbnail_sprite_path = None
        self.thumbnail_vtt_path = None
        self.thumbnail_updated_at = None
        self.thumbnail_error_message = None


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
        self.normalized_path = None
        self.normalized_format = None
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


class MediaChapter(Base):
    __tablename__ = "media_chapters"
    __table_args__ = (
        UniqueConstraint(
            "media_asset_id",
            "chapter_index",
            name="uq_media_chapters_asset_index",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    media_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        index=True,
    )
    chapter_index: Mapped[int] = mapped_column(Integer)
    chapter_id: Mapped[int | None] = mapped_column(BigInteger)
    start_time_seconds: Mapped[float] = mapped_column(Float)
    end_time_seconds: Mapped[float] = mapped_column(Float)
    title: Mapped[str | None] = mapped_column(String(500))

    media_asset: Mapped[MediaAsset] = relationship(
        back_populates="chapters",
    )


class MediaFont(Base):
    __tablename__ = "media_fonts"
    __table_args__ = (UniqueConstraint("sha256", name="uq_media_fonts_sha256"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    name: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    path: Mapped[str] = mapped_column(String(2000))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class MediaAttachment(Base):
    __tablename__ = "media_attachments"
    __table_args__ = (
        UniqueConstraint(
            "media_asset_id",
            "attachment_index",
            name="uq_media_attachments_asset_index",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    media_asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        index=True,
    )
    attachment_index: Mapped[int] = mapped_column(Integer)
    stream_index: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(2000))
    is_font: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    extracted_path: Mapped[str | None] = mapped_column(String(2000))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    font_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media_fonts.id", ondelete="SET NULL"),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=MediaAttachmentStatus.PENDING.value,
        server_default=MediaAttachmentStatus.PENDING.value,
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

    media_asset: Mapped[MediaAsset] = relationship(
        back_populates="attachments",
    )
    font: Mapped[MediaFont | None] = relationship()

    @property
    def processing_status(self) -> MediaAttachmentStatus:
        return MediaAttachmentStatus(self.status)

    def mark_processing(self) -> None:
        self.status = MediaAttachmentStatus.PROCESSING.value
        self.extracted_path = None
        self.size_bytes = None
        self.font_id = None
        self.error_message = None

    def mark_completed(
        self,
        *,
        extracted_path: str,
        size_bytes: int,
        font_id: UUID | None = None,
    ) -> None:
        self.status = MediaAttachmentStatus.COMPLETED.value
        self.extracted_path = extracted_path
        self.size_bytes = size_bytes
        self.font_id = font_id
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        self.status = MediaAttachmentStatus.FAILED.value
        self.error_message = error_message[:2000]

    def retry(self) -> None:
        self.status = MediaAttachmentStatus.PENDING.value
        self.extracted_path = None
        self.size_bytes = None
        self.font_id = None
        self.error_message = None
