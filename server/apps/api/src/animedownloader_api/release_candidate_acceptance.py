from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from animedownloader_anime import Episode, EpisodeNotFoundError
from animedownloader_releases import (
    AnimeMatchStatus,
    EpisodeIngestionStatus,
    ParsedRelease,
    ParserField,
    ParseStatus,
    Release,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .release_candidates import ReleaseCandidateStatus, ReleaseDiscoveryCandidate
from .release_ingestion import EpisodeIngestionService


class ReleaseCandidateNotAcceptableError(ValueError):
    pass


class ReleaseCandidateReplacementTargetError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ReleaseDiscoveryCandidateAcceptanceResult:
    status: EpisodeIngestionStatus
    candidate: ReleaseDiscoveryCandidate
    episode: Episode | None
    existing_episode: Episode | None


class ReleaseDiscoveryCandidateAcceptanceService:
    def __init__(
        self,
        session: AsyncSession,
        ingestion_service: EpisodeIngestionService | None = None,
    ) -> None:
        self.session = session
        self._ingestion_service = ingestion_service or EpisodeIngestionService(session)

    async def accept(
        self,
        candidate_id: UUID,
        *,
        replace_episode_id: UUID | None = None,
    ) -> ReleaseDiscoveryCandidateAcceptanceResult:
        candidate = await self.session.scalar(
            select(ReleaseDiscoveryCandidate)
            .where(ReleaseDiscoveryCandidate.id == candidate_id)
            .with_for_update(),
        )
        if candidate is None:
            raise ValueError(f"release discovery candidate not found: {candidate_id}")

        if candidate.status in {
            ReleaseCandidateStatus.REJECTED.value,
            ReleaseCandidateStatus.STALE.value,
        }:
            raise ReleaseCandidateNotAcceptableError(
                f"candidate status={candidate.status} cannot be accepted",
            )

        release, parsed = _candidate_to_ingestion_data(candidate)

        if parsed.status != ParseStatus.PARSED or not parsed.is_actionable:
            raise ReleaseCandidateNotAcceptableError(
                "candidate must have an actionable parsed release before acceptance",
            )

        if candidate.match_status != AnimeMatchStatus.MATCHED.value:
            raise ReleaseCandidateNotAcceptableError(
                "candidate must have match_status=matched before acceptance",
            )

        if replace_episode_id is not None:
            target_episode = await self.session.scalar(
                select(Episode)
                .where(Episode.id == replace_episode_id)
                .with_for_update(),
            )
            if target_episode is None:
                raise EpisodeNotFoundError(replace_episode_id)
            if target_episode.anime_id != candidate.anime_id:
                raise ReleaseCandidateReplacementTargetError(
                    "replacement Episode must belong to the candidate Anime",
                )
            if target_episode.episode_number != parsed.episode_number:
                raise ReleaseCandidateReplacementTargetError(
                    "replacement Episode number must match the candidate episode number",
                )

        await self.session.rollback()

        if replace_episode_id is None:
            ingestion = await self._ingestion_service.ingest(
                anime_id=candidate.anime_id,
                release=release,
                parsed=parsed,
            )
        else:
            ingestion = await self._ingestion_service.replace(
                episode_id=replace_episode_id,
                release=release,
                parsed=parsed,
            )

        await self.session.rollback()

        if ingestion.status == EpisodeIngestionStatus.REPLACEMENT_CANDIDATE:
            if ingestion.existing_episode is None:
                raise RuntimeError(
                    "replacement candidate ingestion returned no existing Episode",
                )
            async with self.session.begin():
                current_candidate = await self.session.scalar(
                    select(ReleaseDiscoveryCandidate)
                    .where(ReleaseDiscoveryCandidate.id == candidate_id),
                )
                if current_candidate is None:
                    raise ValueError(
                        f"release discovery candidate not found: {candidate_id}",
                    )
                existing_episode = await self.session.scalar(
                    select(Episode).where(
                        Episode.id == ingestion.existing_episode.id,
                    ),
                )
            if existing_episode is None:
                raise EpisodeNotFoundError(ingestion.existing_episode.id)
            return ReleaseDiscoveryCandidateAcceptanceResult(
                status=ingestion.status,
                candidate=current_candidate,
                episode=None,
                existing_episode=existing_episode,
            )

        async with self.session.begin():
            current_candidate = await self.session.scalar(
                select(ReleaseDiscoveryCandidate)
                .where(ReleaseDiscoveryCandidate.id == candidate_id)
                .with_for_update(),
            )
            if current_candidate is None:
                raise ValueError(f"release discovery candidate not found: {candidate_id}")

            current_candidate.status = ReleaseCandidateStatus.ACCEPTED.value
            current_candidate.reviewed_at = datetime.now(UTC)

            episode = None
            if ingestion.episode is not None:
                episode = await self.session.scalar(
                    select(Episode).where(Episode.id == ingestion.episode.id),
                )

        return ReleaseDiscoveryCandidateAcceptanceResult(
            status=ingestion.status,
            candidate=current_candidate,
            episode=episode,
            existing_episode=None,
        )


def _candidate_to_ingestion_data(
    candidate: ReleaseDiscoveryCandidate,
) -> tuple[Release, ParsedRelease]:
    try:
        parsed_status = ParseStatus(candidate.parse_status)
        failed_required_fields = tuple(
            ParserField(field) for field in candidate.failed_required_fields
        )
    except ValueError as exc:
        raise ReleaseCandidateNotAcceptableError(
            "candidate contains invalid persisted parser data",
        ) from exc

    return (
        Release(
            source=candidate.provider_source,
            id=candidate.source_id,
            title=candidate.source_title,
            page_url=candidate.page_url,
            torrent_url=candidate.torrent_url,
            published_at=candidate.published_at,
            size=candidate.size,
            seeders=candidate.seeders,
            leechers=candidate.leechers,
            downloads=candidate.downloads,
            info_hash=candidate.info_hash,
        ),
        ParsedRelease(
            provider_source=candidate.provider_source,
            source_id=candidate.source_id,
            original_title=candidate.source_title,
            normalized_title=candidate.normalized_title,
            release_group=candidate.release_group,
            series_title=candidate.series_title,
            episode_number=candidate.episode_number,
            episode_title=candidate.episode_title,
            season_number=candidate.season_number,
            resolution=candidate.resolution,
            source=candidate.source,
            video_codec=candidate.video_codec,
            audio_codec=candidate.audio_codec,
            bit_depth=candidate.bit_depth,
            status=parsed_status,
            warnings=tuple(candidate.parse_warnings),
            failed_required_fields=failed_required_fields,
            parser_profile_version=candidate.parser_profile_version,
        ),
    )
