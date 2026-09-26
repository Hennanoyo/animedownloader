from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest

from animedownloader_anime import Anime, AnimeService
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_anime_service,
    get_release_discovery_candidate_service,
    get_release_discovery_scheduler,
)
from animedownloader_api.release_candidates import (
    ReleaseCandidateStatus,
    ReleaseDiscoveryCandidate,
    ReleaseDiscoveryRun,
    ReleaseDiscoverySchedule,
)
from animedownloader_api.release_discovery_scheduler import ReleaseDiscoveryScheduler


def make_anime() -> Anime:
    now = datetime(2026, 9, 26, tzinfo=UTC)
    return Anime(
        id=uuid7(),
        title="Frieren",
        titles={"romaji": "Sousou no Frieren"},
        year=2026,
        season="fall",
        weekday="friday",
        air_time=None,
        timezone="Asia/Tokyo",
        created_at=now,
        updated_at=now,
    )


def make_candidate(anime_id) -> ReleaseDiscoveryCandidate:
    now = datetime(2026, 9, 26, tzinfo=UTC)
    return ReleaseDiscoveryCandidate(
        id=uuid7(),
        anime_id=anime_id,
        last_run_id=uuid7(),
        provider_source="nyaa",
        source_id="123456",
        source_title="[ExampleSubs] Frieren - 01 [1080p]",
        page_url="https://nyaa.si/view/123456",
        torrent_url="https://nyaa.si/download/123456.torrent",
        published_at=now,
        size="1 GiB",
        seeders=20,
        leechers=2,
        downloads=100,
        info_hash="abcdef0123456789abcdef0123456789abcdef01",
        normalized_title="[ExampleSubs] Frieren - 01 [1080p]",
        release_group="ExampleSubs",
        series_title="Frieren",
        episode_number=1,
        episode_title=None,
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
            }
        ],
        ranking_score=160,
        ranking_reasons=[
            "Preferred release group",
            "Preferred resolution",
            "Preferred video codec",
            "Preferred source",
        ],
        status="new",
        first_seen_at=now,
        last_seen_at=now,
        reviewed_at=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_list_candidates_returns_normalized_candidate() -> None:
    anime = make_anime()
    candidate = make_candidate(anime.id)
    service = MagicMock()
    service.list_candidates = AsyncMock(return_value=[candidate])

    app = create_app()
    app.dependency_overrides[get_release_discovery_candidate_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/release-discovery/candidates",
            params={"anime_id": str(anime.id), "status": "new"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["source_id"] == "123456"
    assert payload[0]["ranking_score"] == 160
    assert payload[0]["match_candidates"][0]["anime_id"] == str(anime.id)
    service.list_candidates.assert_awaited_once_with(
        anime_id=anime.id,
        status=ReleaseCandidateStatus.NEW,
        limit=100,
    )


@pytest.mark.anyio
async def test_review_candidate_updates_status() -> None:
    anime = make_anime()
    candidate = make_candidate(anime.id)
    candidate.status = "reviewed"
    candidate.reviewed_at = datetime(2026, 9, 26, 1, tzinfo=UTC)
    service = MagicMock()
    service.update_candidate_status = AsyncMock(return_value=candidate)

    app = create_app()
    app.dependency_overrides[get_release_discovery_candidate_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(
            f"/api/release-discovery/candidates/{candidate.id}",
            json={"status": "reviewed"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "reviewed"
    service.update_candidate_status.assert_awaited_once_with(
        candidate.id,
        ReleaseCandidateStatus.REVIEWED,
    )


@pytest.mark.anyio
async def test_schedule_and_manual_run_are_explicit_and_queued() -> None:
    anime = make_anime()
    now = datetime(2026, 9, 26, tzinfo=UTC)
    schedule = ReleaseDiscoverySchedule(
        anime_id=anime.id,
        enabled=True,
        interval_minutes=360,
        next_run_at=now,
        last_run_at=None,
        last_run_status=None,
        created_at=now,
        updated_at=now,
    )
    run = ReleaseDiscoveryRun(
        id=uuid7(),
        anime_id=anime.id,
        scheduled_for=now,
        status="queued",
        query=None,
        search_profile_version=None,
        candidate_count=0,
        warning_count=0,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=now,
    )

    anime_service = MagicMock(spec=AnimeService)
    anime_service.get_anime = AsyncMock(return_value=anime)

    service = MagicMock()
    service.get_schedule = AsyncMock(return_value=schedule)
    service.update_schedule = AsyncMock(return_value=schedule)
    service.create_manual_run = AsyncMock(return_value=run)

    scheduler = MagicMock(spec=ReleaseDiscoveryScheduler)
    scheduler.enqueue_run = AsyncMock()

    app = create_app()
    app.dependency_overrides[get_anime_service] = lambda: anime_service
    app.dependency_overrides[get_release_discovery_candidate_service] = lambda: service
    app.dependency_overrides[get_release_discovery_scheduler] = lambda: scheduler

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        schedule_response = await client.patch(
            f"/api/animes/{anime.id}/release-discovery-schedule",
            json={"enabled": True, "interval_minutes": 360},
        )
        run_response = await client.post(
            f"/api/animes/{anime.id}/release-discovery/run",
            json={},
        )

    assert schedule_response.status_code == 200
    assert schedule_response.json()["interval_minutes"] == 360
    assert run_response.status_code == 202
    assert scheduler.enqueue_run.await_count == 1
    scheduler.enqueue_run.assert_awaited_once_with(run.id)
