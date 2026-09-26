from __future__ import annotations

import uuid
from datetime import datetime, time
from uuid import UUID

from animedownloader_database import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, Time, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Anime(Base):
    __tablename__ = "animes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    title: Mapped[str] = mapped_column(String(200))
    titles: Mapped[dict[str, str]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer)
    season: Mapped[str] = mapped_column(String(16))
    weekday: Mapped[str] = mapped_column(String(16))
    air_time: Mapped[time | None] = mapped_column(Time())
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tokyo")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    episodes: Mapped[list[Episode]] = relationship(
        back_populates="anime",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Episode.episode_number",
    )
    release_preference: Mapped[AnimeReleasePreference | None] = relationship(
        back_populates="anime",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class Episode(Base):
    __tablename__ = "episodes"
    __table_args__ = (
        UniqueConstraint("anime_id", "episode_number", name="uq_episodes_anime_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    anime_id: Mapped[UUID] = mapped_column(
        ForeignKey("animes.id", ondelete="CASCADE"),
        index=True,
    )
    release_group_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("release_groups.id", ondelete="SET NULL"),
        index=True,
    )
    episode_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str | None] = mapped_column(String(256))
    source_title: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(2000))
    torrent_url: Mapped[str] = mapped_column(String(2000))
    size: Mapped[str | None] = mapped_column(String(64))
    seeders: Mapped[int | None] = mapped_column(Integer)
    leechers: Mapped[int | None] = mapped_column(Integer)
    downloads: Mapped[int | None] = mapped_column(Integer)
    info_hash: Mapped[str | None] = mapped_column(String(128))
    download_status: Mapped[str] = mapped_column(String(32), default="not_started")
    conversion_status: Mapped[str] = mapped_column(String(32), default="not_started")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    anime: Mapped[Anime] = relationship(back_populates="episodes")


class AnimeReleasePreference(Base):
    __tablename__ = "anime_release_preferences"

    anime_id: Mapped[UUID] = mapped_column(
        ForeignKey("animes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    release_group_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("release_groups.id", ondelete="SET NULL"),
        index=True,
    )
    resolution: Mapped[str | None] = mapped_column(String(32))
    video_codec: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    anime: Mapped[Anime] = relationship(back_populates="release_preference")
