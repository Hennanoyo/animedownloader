from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from animedownloader_anime import Anime, AnimeReleasePreference
from animedownloader_database import Base
from animedownloader_download import (
    ActiveDownloadJobError,
    DownloadJobService,
    DownloadJobStatus,
)
from animedownloader_releases import (
    AnimeMatchStatus,
    ReleaseGroup,
    normalize_release_group_slug,
)
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from .release_candidate_acceptance import (
    ReleaseCandidateNotAcceptableError,
    ReleaseDiscoveryCandidateAcceptanceService,
)
from .release_candidates import (
    ReleaseCandidateAutomationStatus,
    ReleaseCandidateStatus,
    ReleaseDiscoveryCandidate,
)
from .release_ingestion import ReleaseDoesNotMatchAnimeError


class ReleaseAutomationPolicyError(ValueError):
    pass


class AnimeReleaseAutomationPolicy(Base):
    __tablename__ = "anime_release_automation_policies"
    __table_args__ = (
        CheckConstraint(
            "min_ranking_score >= 0",
            name="ck_anime_release_automation_policies_min_score_nonnegative",
        ),
    )

    anime_id: Mapped[UUID] = mapped_column(
        ForeignKey("animes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    min_ranking_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    require_preference_match: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
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


@dataclass(frozen=True, slots=True)
class ReleaseAutomationCandidatePreview:
    candidate: ReleaseDiscoveryCandidate
    eligible: bool
    reasons: tuple[str, ...]


EnqueueDownload = Callable[[UUID], Awaitable[None]]


class ReleaseCandidateAutomationService:
    CLAIM_TIMEOUT = timedelta(minutes=30)

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_policy(self, anime_id: UUID) -> AnimeReleaseAutomationPolicy:
        anime_exists = await self.session.scalar(
            select(1).where(Anime.id == anime_id),
        )
        if anime_exists is None:
            raise ReleaseAutomationPolicyError(f"anime not found: {anime_id}")

        policy = await self.session.scalar(
            select(AnimeReleaseAutomationPolicy).where(
                AnimeReleaseAutomationPolicy.anime_id == anime_id,
            ),
        )
        if policy is not None:
            return policy
        return AnimeReleaseAutomationPolicy(
            anime_id=anime_id,
            enabled=False,
            min_ranking_score=0,
            require_preference_match=True,
        )

    async def is_enabled(self, anime_id: UUID) -> bool:
        policy = await self.session.scalar(
            select(AnimeReleaseAutomationPolicy.enabled).where(
                AnimeReleaseAutomationPolicy.anime_id == anime_id,
            ),
        )
        return bool(policy)

    async def update_policy(
        self,
        anime_id: UUID,
        *,
        enabled: bool,
        min_ranking_score: int,
        require_preference_match: bool,
    ) -> AnimeReleaseAutomationPolicy:
        if min_ranking_score < 0 or min_ranking_score > 160:
            raise ReleaseAutomationPolicyError(
                "minimum ranking score must be between 0 and 160",
            )

        async with self.session.begin():
            anime_exists = await self.session.scalar(
                select(1).where(Anime.id == anime_id),
            )
            if anime_exists is None:
                raise ReleaseAutomationPolicyError(f"anime not found: {anime_id}")

            policy = await self.session.scalar(
                select(AnimeReleaseAutomationPolicy)
                .where(AnimeReleaseAutomationPolicy.anime_id == anime_id)
                .with_for_update(),
            )
            if policy is None:
                policy = AnimeReleaseAutomationPolicy(anime_id=anime_id)
                self.session.add(policy)

            policy.enabled = enabled
            policy.min_ranking_score = min_ranking_score
            policy.require_preference_match = require_preference_match

        await self.session.refresh(policy)
        return policy

    async def preview(
        self,
        anime_id: UUID,
        *,
        limit: int = 20,
    ) -> list[ReleaseAutomationCandidatePreview]:
        policy = await self.get_policy(anime_id)
        preference, preferred_group = await self._get_preference(anime_id)
        result = await self.session.scalars(
            select(ReleaseDiscoveryCandidate)
            .where(
                ReleaseDiscoveryCandidate.anime_id == anime_id,
                ReleaseDiscoveryCandidate.status.in_(
                    (
                        ReleaseCandidateStatus.NEW.value,
                        ReleaseCandidateStatus.REVIEWED.value,
                    ),
                ),
            )
            .order_by(
                ReleaseDiscoveryCandidate.ranking_score.desc(),
                ReleaseDiscoveryCandidate.last_seen_at.desc(),
                func.lower(ReleaseDiscoveryCandidate.source_title),
            )
            .limit(max(1, min(limit, 100))),
        )
        return [
            self.evaluate_candidate(candidate, policy, preference, preferred_group)
            for candidate in result.all()
        ]

    async def claim_candidates(
        self,
        anime_id: UUID,
        *,
        now: datetime | None = None,
        limit: int = 8,
    ) -> list[UUID]:
        now = now or datetime.now(UTC)
        stale_before = now - self.CLAIM_TIMEOUT

        async with self.session.begin():
            policy = await self.session.scalar(
                select(AnimeReleaseAutomationPolicy)
                .where(AnimeReleaseAutomationPolicy.anime_id == anime_id)
                .with_for_update(),
            )
            if policy is None or not policy.enabled:
                return []

            preference, preferred_group = await self._get_preference(anime_id)
            candidates = await self.session.scalars(
                select(ReleaseDiscoveryCandidate)
                .where(
                    ReleaseDiscoveryCandidate.anime_id == anime_id,
                    or_(
                        (
                            ReleaseDiscoveryCandidate.status.in_(
                                (
                                    ReleaseCandidateStatus.NEW.value,
                                    ReleaseCandidateStatus.REVIEWED.value,
                                ),
                            )
                            & (
                                ReleaseDiscoveryCandidate.automation_status
                                == ReleaseCandidateAutomationStatus.IDLE.value
                            )
                        ),
                        (
                            ReleaseDiscoveryCandidate.status.in_(
                                (
                                    ReleaseCandidateStatus.NEW.value,
                                    ReleaseCandidateStatus.REVIEWED.value,
                                    ReleaseCandidateStatus.ACCEPTED.value,
                                ),
                            )
                            & (
                                ReleaseDiscoveryCandidate.automation_status
                                == ReleaseCandidateAutomationStatus.CLAIMED.value
                            )
                            & (
                                ReleaseDiscoveryCandidate.automation_claimed_at
                                < stale_before
                            )
                        ),
                    ),
                )
                .order_by(
                    ReleaseDiscoveryCandidate.ranking_score.desc(),
                    ReleaseDiscoveryCandidate.last_seen_at.desc(),
                    ReleaseDiscoveryCandidate.id,
                )
                .limit(max(1, min(limit * 4, 100)))
                .with_for_update(skip_locked=True),
            )

            claimed: list[UUID] = []
            for candidate in candidates.all():
                decision = self.evaluate_candidate(
                    candidate,
                    policy,
                    preference,
                    preferred_group,
                )
                if not decision.eligible:
                    continue
                candidate.automation_status = ReleaseCandidateAutomationStatus.CLAIMED.value
                candidate.automation_claimed_at = now
                candidate.automation_error = None
                candidate.automation_completed_at = None
                claimed.append(candidate.id)
                if len(claimed) >= limit:
                    break
            return claimed

    async def list_recovery_anime_ids(
        self,
        *,
        now: datetime | None = None,
        limit: int = 50,
    ) -> list[UUID]:
        stale_before = (now or datetime.now(UTC)) - self.CLAIM_TIMEOUT
        result = await self.session.scalars(
            select(ReleaseDiscoveryCandidate.anime_id)
            .where(
                ReleaseDiscoveryCandidate.automation_status
                == ReleaseCandidateAutomationStatus.CLAIMED.value,
                ReleaseDiscoveryCandidate.automation_claimed_at < stale_before,
            )
            .distinct()
            .limit(max(1, min(limit, 100))),
        )
        return list(result.all())

    async def execute_claimed(
        self,
        candidate_id: UUID,
        *,
        enqueue_download: EnqueueDownload,
    ) -> None:
        candidate = await self.session.scalar(
            select(ReleaseDiscoveryCandidate).where(
                ReleaseDiscoveryCandidate.id == candidate_id,
            ),
        )
        if candidate is None:
            return
        if candidate.automation_status != ReleaseCandidateAutomationStatus.CLAIMED.value:
            return

        policy = await self.session.scalar(
            select(AnimeReleaseAutomationPolicy).where(
                AnimeReleaseAutomationPolicy.anime_id == candidate.anime_id,
            ),
        )
        if policy is None or not policy.enabled:
            await self.block(candidate_id, "automatic download policy is no longer enabled")
            return

        preference, preferred_group = await self._get_preference(candidate.anime_id)
        decision = self.evaluate_candidate(
            candidate,
            policy,
            preference,
            preferred_group,
        )
        if not decision.eligible:
            await self.block(candidate_id, "candidate no longer satisfies the automatic download policy")
            return

        try:
            acceptance = await ReleaseDiscoveryCandidateAcceptanceService(
                self.session,
            ).accept(candidate_id)
        except (
            ReleaseCandidateNotAcceptableError,
            ReleaseDoesNotMatchAnimeError,
        ) as exc:
            await self.block(candidate_id, str(exc))
            return

        if acceptance.episode is None:
            await self.block(
                candidate_id,
                "candidate requires an explicit Episode replacement and cannot be automated",
            )
            return

        episode_id = acceptance.episode.id
        download_service = DownloadJobService(self.session)
        active_job = await download_service.get_active_job(episode_id)
        if active_job is not None:
            if active_job.job_status is DownloadJobStatus.PENDING:
                await enqueue_download(active_job.id)
            await self.complete(candidate_id)
            return

        latest_job = await download_service.get_latest_job(episode_id)
        if latest_job is not None:
            if latest_job.job_status is DownloadJobStatus.COMPLETED:
                await self.complete(candidate_id)
            else:
                await self.block(
                    candidate_id,
                    "Episode already has terminal download history; automatic retry is disabled",
                )
            return

        try:
            job = await download_service.create_job(episode_id)
        except ActiveDownloadJobError:
            await self.complete(candidate_id)
            return

        await enqueue_download(job.id)
        await self.complete(candidate_id)

    async def complete(self, candidate_id: UUID) -> None:
        async with self.session.begin():
            candidate = await self.session.scalar(
                select(ReleaseDiscoveryCandidate)
                .where(ReleaseDiscoveryCandidate.id == candidate_id)
                .with_for_update(),
            )
            if candidate is None:
                return
            candidate.automation_status = ReleaseCandidateAutomationStatus.COMPLETED.value
            candidate.automation_completed_at = datetime.now(UTC)
            candidate.automation_error = None

    async def block(self, candidate_id: UUID, message: str) -> None:
        async with self.session.begin():
            candidate = await self.session.scalar(
                select(ReleaseDiscoveryCandidate)
                .where(ReleaseDiscoveryCandidate.id == candidate_id)
                .with_for_update(),
            )
            if candidate is None:
                return
            candidate.automation_status = ReleaseCandidateAutomationStatus.BLOCKED.value
            candidate.automation_error = message[:2000]
            candidate.automation_completed_at = datetime.now(UTC)

    async def _get_preference(
        self,
        anime_id: UUID,
    ) -> tuple[AnimeReleasePreference | None, ReleaseGroup | None]:
        result = await self.session.execute(
            select(AnimeReleasePreference, ReleaseGroup)
            .outerjoin(
                ReleaseGroup,
                ReleaseGroup.id == AnimeReleasePreference.release_group_id,
            )
            .where(AnimeReleasePreference.anime_id == anime_id),
        )
        row = result.first()
        if row is None:
            return None, None
        return row[0], row[1]

    @staticmethod
    def evaluate_candidate(
        candidate: ReleaseDiscoveryCandidate,
        policy: AnimeReleaseAutomationPolicy,
        preference: AnimeReleasePreference | None,
        preferred_group: ReleaseGroup | None,
    ) -> ReleaseAutomationCandidatePreview:
        reasons: list[str] = []
        eligible = policy.enabled

        if not policy.enabled:
            reasons.append("Automation is disabled")
            eligible = False

        if candidate.parse_status != "parsed" or candidate.episode_number is None:
            reasons.append("Release is not an actionable parsed episode")
            eligible = False

        if candidate.match_status != AnimeMatchStatus.MATCHED.value:
            reasons.append("Release is not uniquely matched to this Anime")
            eligible = False

        if candidate.ranking_score < policy.min_ranking_score:
            reasons.append(
                f"Ranking score {candidate.ranking_score} is below the minimum "
                f"{policy.min_ranking_score}",
            )
            eligible = False

        configured_matches = 0
        configured_fields = 0

        if preference is not None:
            if preference.release_group_id is not None:
                configured_fields += 1
                if (
                    preferred_group is not None
                    and preferred_group.enabled
                    and candidate.release_group
                    and normalize_release_group_slug(candidate.release_group)
                    == preferred_group.slug
                ):
                    configured_matches += 1
                else:
                    reasons.append("Preferred release group does not match")

            for label, configured, actual in (
                ("resolution", preference.resolution, candidate.resolution),
                ("video codec", preference.video_codec, candidate.video_codec),
                ("source", preference.source, candidate.source),
            ):
                if configured:
                    configured_fields += 1
                    if actual and actual.casefold() == configured.casefold():
                        configured_matches += 1
                    else:
                        reasons.append(f"Preferred {label} does not match")

        if (
            policy.require_preference_match
            and configured_fields > 0
            and configured_matches != configured_fields
        ):
            eligible = False

        if policy.require_preference_match and configured_fields == 0:
            eligible = False
            reasons.append("No release preference is configured")

        if eligible and not any(
            reason.endswith("does not match")
            or reason.startswith("Ranking score")
            or reason.startswith("Release is")
            for reason in reasons
        ):
            reasons.append("Candidate satisfies the automatic download policy")

        return ReleaseAutomationCandidatePreview(
            candidate=candidate,
            eligible=eligible,
            reasons=tuple(reasons),
        )
