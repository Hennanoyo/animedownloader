from __future__ import annotations

from datetime import datetime
from uuid import UUID

from animedownloader_database import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column


class ReleaseDiscoverySchedule(Base):
    """Per-Anime persisted Discovery configuration and execution schedule."""

    __tablename__ = "release_discovery_schedules"

    anime_id: Mapped[UUID] = mapped_column(
        ForeignKey("animes.id", ondelete="CASCADE"),
        primary_key=True,
    )

    search_title_source: Mapped[str | None] = mapped_column(String(16))
    search_title: Mapped[str | None] = mapped_column(String(200))
    search_field_order: Mapped[list[str] | None] = mapped_column(JSON)
    search_enabled_fields: Mapped[list[str] | None] = mapped_column(JSON)
    search_group: Mapped[str | None] = mapped_column(String(128))
    search_episode: Mapped[int | None] = mapped_column(Integer)
    search_resolution: Mapped[str | None] = mapped_column(String(32))
    search_codec: Mapped[str | None] = mapped_column(String(32))
    search_source: Mapped[str | None] = mapped_column(String(32))

    automation_mode: Mapped[str] = mapped_column(
        String(16),
        default="off",
        server_default="off",
    )
    automation_min_ranking_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    automation_require_plan_match: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )

    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    interval_minutes: Mapped[int] = mapped_column(Integer, default=360, server_default="360")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_status: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


def has_saved_search_plan(schedule: ReleaseDiscoverySchedule) -> bool:
    return bool(
        schedule.search_title
        and schedule.search_field_order
        and schedule.search_enabled_fields
    )
