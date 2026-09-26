from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID

from animedownloader_releases import AnimeMatchResult
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from animedownloader_database import Base

from .release_discovery import ReleaseDiscoveryResult


class ReleaseDiscoverySchedule(Base):
    __tablename__ = "release_discovery_schedules"

    anime_id: Mapped[UUID] = mapped_column(
        ForeignKey("animes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(default=False, server_default="false")
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


class ReleaseDiscoveryRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReleaseCandidateStatus(StrEnum):
    NEW = "new"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    STALE = "stale"


class ReleaseDiscoveryRun(Base):
    __tablename__ = "release_discovery_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    anime_id: Mapped[UUID] = mapped_column(
        ForeignKey("animes.id", ondelete="CASCADE"),
        index=True,
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        default=ReleaseDiscoveryRunStatus.QUEUED.value,
    )
    query: Mapped[str | None] = mapped_column(String(500))
    search_profile_version: Mapped[int | None] = mapped_column(Integer)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    warning_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(String(2000))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "anime_id",
            "scheduled_for",
            name="uq_release_discovery_runs_anime_scheduled_for",
        ),
    )


class ReleaseDiscoveryCandidate(Base):
    __tablename__ = "release_discovery_candidates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    anime_id: Mapped[UUID] = mapped_column(
        ForeignKey("animes.id", ondelete="CASCADE"),
        index=True,
    )
    last_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("release_discovery_runs.id", ondelete="SET NULL"),
        index=True,
    )

    provider_source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(256))
    source_title: Mapped[str] = mapped_column(String(500))
    page_url: Mapped[str] = mapped_column(String(2000))
    torrent_url: Mapped[str] = mapped_column(String(2000))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    size: Mapped[str | None] = mapped_column(String(64))
    seeders: Mapped[int | None] = mapped_column(Integer)
    leechers: Mapped[int | None] = mapped_column(Integer)
    downloads: Mapped[int | None] = mapped_column(Integer)
    info_hash: Mapped[str | None] = mapped_column(String(128))

    normalized_title: Mapped[str] = mapped_column(String(500))
    release_group: Mapped[str | None] = mapped_column(String(128))
    series_title: Mapped[str | None] = mapped_column(String(300))
    episode_number: Mapped[int | None] = mapped_column(Integer)
    episode_title: Mapped[str | None] = mapped_column(String(300))
    season_number: Mapped[int | None] = mapped_column(Integer)
    resolution: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(String(32))
    video_codec: Mapped[str | None] = mapped_column(String(32))
    audio_codec: Mapped[str | None] = mapped_column(String(32))
    bit_depth: Mapped[int | None] = mapped_column(Integer)
    parse_status: Mapped[str] = mapped_column(String(16))
    parse_warnings: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
    )
    failed_required_fields: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
    )
    parser_profile_version: Mapped[int | None] = mapped_column(Integer)

    normalized_series_title: Mapped[str | None] = mapped_column(String(300))
    match_status: Mapped[str] = mapped_column(String(16))
    match_candidates: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
    )
    ranking_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ranking_reasons: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
    )

    status: Mapped[str] = mapped_column(
        String(16),
        default=ReleaseCandidateStatus.NEW.value,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "anime_id",
            "provider_source",
            "source_id",
            name="uq_release_discovery_candidates_identity",
        ),
    )


@dataclass(frozen=True, slots=True)
class ReleaseDiscoveryRunResult:
    candidate_count: int
    warning_count: int


class ReleaseDiscoveryCandidateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start_run(self, run_id: UUID) -> ReleaseDiscoveryRun:
        async with self.session.begin():
            run = await self.session.scalar(
                select(ReleaseDiscoveryRun)
                .where(ReleaseDiscoveryRun.id == run_id)
                .with_for_update(),
            )
            if run is None:
                raise ValueError(f"release discovery run not found: {run_id}")
            if run.status != ReleaseDiscoveryRunStatus.QUEUED.value:
                return run

            run.status = ReleaseDiscoveryRunStatus.RUNNING.value
            run.started_at = datetime.now(timezone.utc)

        return run

    async def complete_run(
        self,
        run_id: UUID,
        result: ReleaseDiscoveryRunResult,
    ) -> None:
        async with self.session.begin():
            run = await self.session.scalar(
                select(ReleaseDiscoveryRun)
                .where(ReleaseDiscoveryRun.id == run_id)
                .with_for_update(),
            )
            if run is None:
                raise ValueError(f"release discovery run not found: {run_id}")
            completed_at = datetime.now(timezone.utc)
            run.status = ReleaseDiscoveryRunStatus.COMPLETED.value
            run.candidate_count = result.candidate_count
            run.warning_count = result.warning_count
            run.completed_at = completed_at
            schedule = await self.session.scalar(
                select(ReleaseDiscoverySchedule)
                .where(ReleaseDiscoverySchedule.anime_id == run.anime_id)
                .with_for_update(),
            )
            if schedule is not None:
                schedule.last_run_at = completed_at
                schedule.last_run_status = ReleaseDiscoveryRunStatus.COMPLETED.value

    async def fail_run(self, run_id: UUID, message: str) -> None:
        async with self.session.begin():
            run = await self.session.scalar(
                select(ReleaseDiscoveryRun)
                .where(ReleaseDiscoveryRun.id == run_id)
                .with_for_update(),
            )
            if run is None:
                raise ValueError(f"release discovery run not found: {run_id}")
            completed_at = datetime.now(timezone.utc)
            run.status = ReleaseDiscoveryRunStatus.FAILED.value
            run.error_message = message[:2000]
            run.completed_at = completed_at
            schedule = await self.session.scalar(
                select(ReleaseDiscoverySchedule)
                .where(ReleaseDiscoverySchedule.anime_id == run.anime_id)
                .with_for_update(),
            )
            if schedule is not None:
                schedule.last_run_at = completed_at
                schedule.last_run_status = ReleaseDiscoveryRunStatus.FAILED.value

    async def record_discovery(
        self,
        run_id: UUID,
        result: ReleaseDiscoveryResult,
    ) -> ReleaseDiscoveryRunResult:
        async with self.session.begin():
            run = await self.session.scalar(
                select(ReleaseDiscoveryRun)
                .where(ReleaseDiscoveryRun.id == run_id)
                .with_for_update(),
            )
            if run is None:
                raise ValueError(f"release discovery run not found: {run_id}")

            run.query = result.query
            run.search_profile_version = result.search_profile_version

            observed_at = datetime.now(timezone.utc)
            for item in result.items:
                candidate = await self.session.scalar(
                    select(ReleaseDiscoveryCandidate)
                    .where(
                        ReleaseDiscoveryCandidate.anime_id == run.anime_id,
                        ReleaseDiscoveryCandidate.provider_source
                        == item.release.source,
                        ReleaseDiscoveryCandidate.source_id == item.release.id,
                    )
                    .with_for_update()
                )
                if candidate is None:
                    candidate = ReleaseDiscoveryCandidate(
                        anime_id=run.anime_id,
                        provider_source=item.release.source,
                        source_id=item.release.id,
                        source_title=item.release.title,
                        page_url=item.release.page_url,
                        torrent_url=item.release.torrent_url,
                        first_seen_at=observed_at,
                        status=ReleaseCandidateStatus.NEW.value,
                    )
                    self.session.add(candidate)

                candidate.last_run_id = run.id
                candidate.source_title = item.release.title
                candidate.page_url = item.release.page_url
                candidate.torrent_url = item.release.torrent_url
                candidate.published_at = item.release.published_at
                candidate.size = item.release.size
                candidate.seeders = item.release.seeders
                candidate.leechers = item.release.leechers
                candidate.downloads = item.release.downloads
                candidate.info_hash = item.release.info_hash

                candidate.normalized_title = item.parsed.normalized_title
                candidate.release_group = item.parsed.release_group
                candidate.series_title = item.parsed.series_title
                candidate.episode_number = item.parsed.episode_number
                candidate.episode_title = item.parsed.episode_title
                candidate.season_number = item.parsed.season_number
                candidate.resolution = item.parsed.resolution
                candidate.source = item.parsed.source
                candidate.video_codec = item.parsed.video_codec
                candidate.audio_codec = item.parsed.audio_codec
                candidate.bit_depth = item.parsed.bit_depth
                candidate.parse_status = item.parsed.status.value
                candidate.parse_warnings = list(item.parsed.warnings)
                candidate.failed_required_fields = [
                    field.value for field in item.parsed.failed_required_fields
                ]
                candidate.parser_profile_version = item.parsed.parser_profile_version

                candidate.normalized_series_title = item.match.normalized_series_title
                candidate.match_status = item.match.status.value
                candidate.match_candidates = _serialize_match(item.match)
                candidate.ranking_score = item.ranking.score
                candidate.ranking_reasons = list(item.ranking.reasons)
                candidate.last_seen_at = observed_at

            return ReleaseDiscoveryRunResult(
                candidate_count=len(result.items),
                warning_count=len(result.warnings),
            )

    async def list_candidates(
        self,
        *,
        anime_id: UUID | None = None,
        status: ReleaseCandidateStatus | None = None,
        limit: int = 100,
    ) -> list[ReleaseDiscoveryCandidate]:
        statement = select(ReleaseDiscoveryCandidate).order_by(
            ReleaseDiscoveryCandidate.ranking_score.desc(),
            ReleaseDiscoveryCandidate.last_seen_at.desc(),
            func.lower(ReleaseDiscoveryCandidate.source_title),
        )
        if anime_id is not None:
            statement = statement.where(ReleaseDiscoveryCandidate.anime_id == anime_id)
        if status is not None:
            statement = statement.where(
                ReleaseDiscoveryCandidate.status == status.value,
            )
        result = await self.session.scalars(statement.limit(max(1, min(limit, 200))))
        return list(result.all())

    async def list_runs(
        self,
        *,
        anime_id: UUID | None = None,
        limit: int = 20,
    ) -> list[ReleaseDiscoveryRun]:
        statement = select(ReleaseDiscoveryRun).order_by(
            ReleaseDiscoveryRun.created_at.desc(),
        )
        if anime_id is not None:
            statement = statement.where(ReleaseDiscoveryRun.anime_id == anime_id)
        result = await self.session.scalars(statement.limit(max(1, min(limit, 100))))
        return list(result.all())

    async def get_run(self, run_id: UUID) -> ReleaseDiscoveryRun | None:
        return await self.session.scalar(
            select(ReleaseDiscoveryRun).where(ReleaseDiscoveryRun.id == run_id),
        )

    async def get_schedule(self, anime_id: UUID) -> ReleaseDiscoverySchedule:
        schedule = await self.session.scalar(
            select(ReleaseDiscoverySchedule).where(
                ReleaseDiscoverySchedule.anime_id == anime_id,
            ),
        )
        if schedule is not None:
            return schedule
        return ReleaseDiscoverySchedule(anime_id=anime_id)

    async def update_schedule(
        self,
        anime_id: UUID,
        *,
        enabled: bool,
        interval_minutes: int,
    ) -> ReleaseDiscoverySchedule:
        if interval_minutes < 15 or interval_minutes > 1440:
            raise ValueError("interval must be between 15 and 1440 minutes")

        async with self.session.begin():
            schedule = await self.session.scalar(
                select(ReleaseDiscoverySchedule)
                .where(ReleaseDiscoverySchedule.anime_id == anime_id)
                .with_for_update(),
            )
            if schedule is None:
                schedule = ReleaseDiscoverySchedule(anime_id=anime_id)
                self.session.add(schedule)

            schedule.enabled = enabled
            schedule.interval_minutes = interval_minutes
            schedule.next_run_at = (
                datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
                if enabled
                else None
            )

        await self.session.refresh(schedule)
        return schedule

    async def create_manual_run(self, anime_id: UUID) -> ReleaseDiscoveryRun:
        async with self.session.begin():
            active = await self.session.scalar(
                select(ReleaseDiscoveryRun)
                .where(
                    ReleaseDiscoveryRun.anime_id == anime_id,
                    ReleaseDiscoveryRun.status.in_(
                        [
                            ReleaseDiscoveryRunStatus.QUEUED.value,
                            ReleaseDiscoveryRunStatus.RUNNING.value,
                        ],
                    ),
                )
                .order_by(ReleaseDiscoveryRun.created_at.desc())
                .limit(1)
                .with_for_update(),
            )
            if active is not None:
                return active

            run = ReleaseDiscoveryRun(
                anime_id=anime_id,
                scheduled_for=datetime.now(timezone.utc),
            )
            self.session.add(run)
            await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_candidate_status(
        self,
        candidate_id: UUID,
        status: ReleaseCandidateStatus,
    ) -> ReleaseDiscoveryCandidate:
        if status == ReleaseCandidateStatus.ACCEPTED:
            raise ValueError("candidate acceptance is reserved for the explicit acceptance phase")

        async with self.session.begin():
            candidate = await self.session.scalar(
                select(ReleaseDiscoveryCandidate)
                .where(ReleaseDiscoveryCandidate.id == candidate_id)
                .with_for_update(),
            )
            if candidate is None:
                raise ValueError(f"release discovery candidate not found: {candidate_id}")
            candidate.status = status.value
            candidate.reviewed_at = datetime.now(timezone.utc)

        await self.session.refresh(candidate)
        return candidate

    @staticmethod
    def _anime_id(run: ReleaseDiscoveryRun) -> UUID:
        return run.anime_id


def _serialize_match(match: AnimeMatchResult) -> list[dict[str, object]]:
    return [
        {
            "anime_id": str(candidate.anime_id),
            "title": candidate.title,
            "matched_titles": list(candidate.matched_titles),
        }
        for candidate in match.candidates
    ]
