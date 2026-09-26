from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid7

import pytest
from animedownloader_anime import Episode
from animedownloader_api.release_candidate_acceptance import (
    ReleaseCandidateNotAcceptableError,
    ReleaseDiscoveryCandidateAcceptanceService,
)
from animedownloader_api.release_candidates import ReleaseDiscoveryCandidate
from animedownloader_api.release_ingestion import EpisodeIngestionResult
from animedownloader_releases import EpisodeIngestionStatus
from sqlalchemy.ext.asyncio import AsyncSession


class FakeSession:
    def __init__(self, scalar_results: list[object | None]) -> None:
        self.scalar_results = scalar_results
        self.rollback_count = 0

    def begin(self) -> "FakeSession":
        return self

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def scalar(self, _statement: object) -> object | None:
        if not self.scalar_results:
            return None
        return self.scalar_results.pop(0)

    async def rollback(self) -> None:
        self.rollback_count += 1


def _candidate(
    anime_id: UUID,
    *,
    status: str = "reviewed",
    episode_number: int = 8,
) -> ReleaseDiscoveryCandidate:
    now = datetime(2026, 9, 26, tzinfo=UTC)
    return ReleaseDiscoveryCandidate(
        id=uuid7(),
        anime_id=anime_id,
        last_run_id=uuid7(),
        provider_source="nyaa",
        source_id="release-8",
        source_title="[ExampleSubs] Frieren - 08 [1080p][HEVC]",
        page_url="https://nyaa.si/view/8",
        torrent_url="https://nyaa.si/download/8.torrent",
        published_at=now,
        size="1.2 GiB",
        seeders=20,
        leechers=2,
        downloads=100,
        info_hash="hash-8",
        normalized_title="frieren 08",
        release_group="ExampleSubs",
        series_title="Frieren",
        episode_number=episode_number,
        episode_title="Departure",
        season_number=None,
        resolution="1080p",
        source="WEB",
        video_codec="HEVC",
        audio_codec="AAC",
        bit_depth=10,
        parse_status="parsed",
        parse_warnings=[],
        failed_required_fields=[],
        parser_profile_version=1,
        normalized_series_title="frieren",
        match_status="matched",
        match_candidates=[
            {
                "anime_id": str(anime_id),
                "title": "Frieren",
                "matched_titles": ["Frieren"],
            },
        ],
        ranking_score=160,
        ranking_reasons=["Preferred release group"],
        status=status,
        first_seen_at=now,
        last_seen_at=now,
        reviewed_at=now,
        created_at=now,
        updated_at=now,
    )


def _episode(anime_id: UUID, *, episode_number: int = 8) -> Episode:
    now = datetime(2026, 9, 26, tzinfo=UTC)
    return Episode(
        id=uuid7(),
        anime_id=anime_id,
        episode_number=episode_number,
        title="Episode 8",
        source="nyaa",
        source_id="old-release",
        source_title="Old release",
        source_url="https://nyaa.si/view/old",
        torrent_url="https://nyaa.si/download/old.torrent",
        size="1 GiB",
        seeders=1,
        leechers=1,
        downloads=1,
        info_hash="old-hash",
        download_status="not_started",
        conversion_status="not_started",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_accept_creates_episode_and_marks_candidate_accepted() -> None:
    anime_id = uuid7()
    candidate = _candidate(anime_id)
    episode = _episode(anime_id)
    accepted_candidate = _candidate(anime_id, status="accepted")
    accepted_candidate.id = candidate.id
    ingestion = AsyncMock(
        return_value=EpisodeIngestionResult(
            status=EpisodeIngestionStatus.CREATED,
            episode=episode,
            existing_episode=None,
        ),
    )
    session = FakeSession([candidate, accepted_candidate, episode])
    service = ReleaseDiscoveryCandidateAcceptanceService(
        cast(AsyncSession, session),
        ingestion_service=ingestion,
    )

    result = await service.accept(candidate.id)

    assert result.status is EpisodeIngestionStatus.CREATED
    assert result.candidate.status == "accepted"
    assert result.episode is episode
    assert result.existing_episode is None
    ingestion.ingest.assert_awaited_once()
    assert session.rollback_count == 2


@pytest.mark.anyio
async def test_accept_returns_replacement_candidate_without_mutation() -> None:
    anime_id = uuid7()
    candidate = _candidate(anime_id)
    existing_episode = _episode(anime_id)
    ingestion = AsyncMock(
        return_value=EpisodeIngestionResult(
            status=EpisodeIngestionStatus.REPLACEMENT_CANDIDATE,
            episode=None,
            existing_episode=existing_episode,
        ),
    )
    session = FakeSession([candidate, candidate, existing_episode])
    service = ReleaseDiscoveryCandidateAcceptanceService(
        cast(AsyncSession, session),
        ingestion_service=ingestion,
    )

    result = await service.accept(candidate.id)

    assert result.status is EpisodeIngestionStatus.REPLACEMENT_CANDIDATE
    assert result.candidate.status == "reviewed"
    assert result.episode is None
    assert result.existing_episode is existing_episode
    ingestion.ingest.assert_awaited_once()
    assert session.rollback_count == 2


@pytest.mark.anyio
async def test_accept_can_explicitly_replace_the_existing_episode() -> None:
    anime_id = uuid7()
    candidate = _candidate(anime_id)
    existing_episode = _episode(anime_id)
    accepted_candidate = _candidate(anime_id, status="accepted")
    accepted_candidate.id = candidate.id
    replaced_episode = _episode(anime_id)
    replaced_episode.id = existing_episode.id
    ingestion = AsyncMock(
        return_value=EpisodeIngestionResult(
            status=EpisodeIngestionStatus.REPLACED,
            episode=replaced_episode,
            existing_episode=None,
        ),
    )
    session = FakeSession([candidate, existing_episode, accepted_candidate, replaced_episode])
    service = ReleaseDiscoveryCandidateAcceptanceService(
        cast(AsyncSession, session),
        ingestion_service=ingestion,
    )

    result = await service.accept(
        candidate.id,
        replace_episode_id=existing_episode.id,
    )

    assert result.status is EpisodeIngestionStatus.REPLACED
    assert result.candidate.status == "accepted"
    assert result.episode is replaced_episode
    ingestion.replace.assert_awaited_once()
    assert session.rollback_count == 2


@pytest.mark.anyio
async def test_rejected_candidate_cannot_be_accepted() -> None:
    anime_id = uuid7()
    candidate = _candidate(anime_id, status="rejected")
    session = FakeSession([candidate])
    service = ReleaseDiscoveryCandidateAcceptanceService(cast(AsyncSession, session))

    with pytest.raises(ReleaseCandidateNotAcceptableError):
        await service.accept(candidate.id)
