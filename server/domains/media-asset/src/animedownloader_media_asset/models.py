from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from animedownloader_database import Base
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column


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
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    frame_rate: Mapped[str | None] = mapped_column(String(32))
    audio_codec: Mapped[str | None] = mapped_column(String(64))
    audio_channels: Mapped[int | None] = mapped_column(Integer)
    audio_sample_rate_hz: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
