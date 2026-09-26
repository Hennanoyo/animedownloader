from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from animedownloader_anime import Anime, AnimeNotFoundError, AnimeReleasePreference
from animedownloader_database import Base
from animedownloader_releases import (
    AnimeMatchResult,
    ReleaseGroup,
    normalize_release_group_slug,
)
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .release_discovery import ReleaseDiscoveryResult
from .release_discovery_config import ReleaseDiscoverySchedule


class ReleaseDiscoveryQueryStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"




class ReleaseDiscoveryQuery(Base):
    __tablename__ = "release_discovery_queries"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "position",
            name="uq_release_discovery_queries_run_position",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("release_discovery_runs.id", ondelete="CASCADE"),
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer)
    query: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(16))
    result_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    result_cap_reached: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    error_message: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    run: Mapped[ReleaseDiscoveryRun] = relationship(back_populates="queries")

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


class ReleaseCandidateAutomationStatus(StrEnum):
    IDLE = "idle"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    BLOCKED = "blocked"


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
    queries: Mapped[list[ReleaseDiscoveryQuery]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ReleaseDiscoveryQuery.position",
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
    automation_status: Mapped[str] = mapped_column(
        String(16),
        default=ReleaseCandidateAutomationStatus.IDLE.value,
        server_default=ReleaseCandidateAutomationStatus.IDLE.value,
    )
    automation_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    automation_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    automation_error: Mapped[str | None] = mapped_column(String(2000))
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
            run.started_at = datetime.now(UTC)

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
            completed_at = datetime.now(UTC)
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
            completed_at = datetime.now(UTC)
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

            for query_result in result.query_results:
                self.session.add(
                    ReleaseDiscoveryQuery(
                        run_id=run.id,
                        position=query_result.position,
                        query=query_result.query,
                        status=query_result.status,
                        result_count=query_result.result_count,
                        result_cap_reached=query_result.result_cap_reached,
                        error_message=query_result.error_message,
                    ),
                )

            observed_at = datetime.now(UTC)
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
        return ReleaseDiscoverySchedule(
            anime_id=anime_id,
            enabled=False,
            interval_minutes=360,
        )

    async def update_schedule(
        self,
        anime_id: UUID,
        *,
        enabled: bool | None = None,
        interval_minutes: int | None = None,
        search_title_source: str | None = None,
        search_title: str | None = None,
        search_field_order: list[str] | None = None,
        search_enabled_fields: list[str] | None = None,
        search_group: str | None = None,
        search_episode: int | None = None,
        search_resolution: str | None = None,
        search_codec: str | None = None,
        search_source: str | None = None,
    ) -> ReleaseDiscoverySchedule:
        if interval_minutes is not None and not 15 <= interval_minutes <= 1440:
            raise ValueError("interval must be between 15 and 1440 minutes")

        allowed_fields = {"group", "title", "episode", "resolution", "codec", "source"}
        if search_field_order is not None:
            ordered_fields = [str(item) for item in search_field_order]
            enabled_fields = [str(item) for item in (search_enabled_fields or [])]
            if (
                len(ordered_fields) != len(allowed_fields)
                or set(ordered_fields) != allowed_fields
                or len(enabled_fields) == 0
                or not set(enabled_fields).issubset(allowed_fields)
                or len(set(enabled_fields)) != len(enabled_fields)
            ):
                raise ValueError("search plan fields are invalid")
        elif search_enabled_fields is not None:
            raise ValueError("search field order is required with enabled fields")

        plan_supplied = search_title is not None or search_field_order is not None
        if plan_supplied and (
            search_title is None
            or search_title_source is None
            or search_field_order is None
            or search_enabled_fields is None
        ):
            raise ValueError("complete search plan is required")
        if search_title is not None and not search_title.strip():
            raise ValueError("search title must not be empty")

        async with self.session.begin():
            anime = await self.session.scalar(
                select(Anime).where(Anime.id == anime_id),
            )
            if anime is None:
                raise AnimeNotFoundError(anime_id)

            schedule = await self.session.scalar(
                select(ReleaseDiscoverySchedule)
                .where(ReleaseDiscoverySchedule.anime_id == anime_id)
                .with_for_update(),
            )
            if schedule is None:
                schedule = ReleaseDiscoverySchedule(anime_id=anime_id)
                self.session.add(schedule)

            if enabled is not None:
                schedule.enabled = enabled
                schedule.next_run_at = (
                    datetime.now(UTC)
                    + timedelta(minutes=interval_minutes or schedule.interval_minutes)
                    if enabled
                    else None
                )

            if interval_minutes is not None:
                schedule.interval_minutes = interval_minutes
                if schedule.enabled:
                    schedule.next_run_at = datetime.now(UTC) + timedelta(
                        minutes=interval_minutes,
                    )

            if plan_supplied:
                schedule.search_title_source = search_title_source.strip() or "custom"
                schedule.search_title = search_title.strip()
                schedule.search_field_order = [str(item) for item in search_field_order]
                schedule.search_enabled_fields = [str(item) for item in search_enabled_fields]
                schedule.search_group = search_group.strip() if search_group else None
                schedule.search_episode = search_episode
                schedule.search_resolution = (
                    search_resolution.strip() if search_resolution else None
                )
                schedule.search_codec = search_codec.strip() if search_codec else None
                schedule.search_source = search_source.strip() if search_source else None

                # Keep the legacy preference row as derived ranking state so
                # existing candidate ranking/automation remains compatible.
                preference = await self.session.scalar(
                    select(AnimeReleasePreference).where(
                        AnimeReleasePreference.anime_id == anime_id,
                    ),
                )
                if preference is None:
                    preference = AnimeReleasePreference(anime_id=anime_id)
                    self.session.add(preference)

                preferred_group_id = None
                if "group" in schedule.search_enabled_fields and schedule.search_group:
                    group_slug = normalize_release_group_slug(schedule.search_group)
                    preferred_group_id = await self.session.scalar(
                        select(ReleaseGroup.id)
                        .where(
                            ReleaseGroup.enabled.is_(True),
                            (
                                (ReleaseGroup.slug == group_slug)
                                | (
                                    func.lower(ReleaseGroup.name)
                                    == schedule.search_group.casefold()
                                )
                            ),
                        )
                        .limit(1),
                    )

                enabled_fields = set(schedule.search_enabled_fields)
                preference.release_group_id = (
                    preferred_group_id if "group" in enabled_fields else None
                )
                preference.resolution = (
                    schedule.search_resolution
                    if "resolution" in enabled_fields
                    else None
                )
                preference.video_codec = (
                    schedule.search_codec if "codec" in enabled_fields else None
                )
                preference.source = (
                    schedule.search_source if "source" in enabled_fields else None
                )

        await self.session.refresh(schedule)
        return schedule

    async def create_manual_run(self, anime_id: UUID) -> ReleaseDiscoveryRun:
        async with self.session.begin():
            anime_exists = await self.session.scalar(
                select(1).where(Anime.id == anime_id),
            )
            if anime_exists is None:
                raise AnimeNotFoundError(anime_id)

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
                scheduled_for=datetime.now(UTC),
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
            candidate.reviewed_at = datetime.now(UTC)

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
