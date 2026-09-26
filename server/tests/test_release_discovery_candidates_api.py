from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid7

import httpx
import pytest
from animedownloader_anime import Anime, AnimeService
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import (
    get_anime_service,
    get_release_candidate_automation_service,
    get_release_candidate_automation_task_dispatcher,
    get_release_discovery_candidate_acceptance_service,
    get_release_discovery_candidate_service,
    get_release_discovery_scheduler,
)
from animedownloader_api.release_candidate_acceptance import (
    ReleaseDiscoveryCandidateAcceptanceResult,
    ReleaseDiscoveryCandidateAcceptanceService,
)
from animedownloader_api.release_candidate_automation import (
    AnimeReleaseAutomationPolicy,
    ReleaseAutomationCandidatePreview,
    ReleaseCandidateAutomationService,
)
from animedownloader_api.release_candidates import (
    ReleaseCandidateStatus,
    ReleaseDiscoveryCandidate,
    ReleaseDiscoveryRun,
    ReleaseDiscoverySchedule,
)
from animedownloader_api.release_discovery_scheduler import ReleaseDiscoveryScheduler
from animedownloader_releases import EpisodeIngestionStatus


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


def make_candidate(anime_id: UUID) -> ReleaseDiscoveryCandidate:
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



@pytest.mark.anyio
async def test_automation_policy_can_be_saved_and_previewed() -> None:
    anime = make_anime()
    now = datetime(2026, 9, 26, tzinfo=UTC)
    policy = AnimeReleaseAutomationPolicy(
        anime_id=anime.id,
        enabled=True,
        min_ranking_score=100,
        require_preference_match=True,
        created_at=now,
        updated_at=now,
    )
    preview = ReleaseAutomationCandidatePreview(
        candidate=make_candidate(anime.id),
        eligible=True,
        reasons=("Candidate satisfies the automatic download policy",),
    )

    service = MagicMock(spec=ReleaseCandidateAutomationService)
    service.get_policy = AsyncMock(return_value=policy)
    service.update_policy = AsyncMock(return_value=policy)
    service.preview = AsyncMock(return_value=[preview])

    dispatcher = MagicMock()
    dispatcher.enqueue = AsyncMock()

    app = create_app()
    app.dependency_overrides[get_release_candidate_automation_service] = lambda: service
    app.dependency_overrides[get_release_candidate_automation_task_dispatcher] = (
        lambda: dispatcher
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        patch_response = await client.patch(
            f"/api/animes/{anime.id}/release-automation-policy",
            json={
                "enabled": True,
                "min_ranking_score": 100,
                "require_preference_match": True,
            },
        )
        preview_response = await client.get(
            f"/api/animes/{anime.id}/release-automation-preview",
        )
        run_response = await client.post(
            f"/api/animes/{anime.id}/release-automation/run",
            json={},
        )

    assert patch_response.status_code == 200
    assert patch_response.json()["enabled"] is True
    assert patch_response.json()["min_ranking_score"] == 100
    assert preview_response.status_code == 200
    assert preview_response.json()[0]["eligible"] is True
    assert run_response.status_code == 202
    dispatcher.enqueue.assert_awaited_once_with(anime.id)


@pytest.mark.anyio
async def test_disabled_automation_cannot_be_started() -> None:
    anime = make_anime()
    now = datetime(2026, 9, 26, tzinfo=UTC)
    policy = AnimeReleaseAutomationPolicy(
        anime_id=anime.id,
        enabled=False,
        min_ranking_score=0,
        require_preference_match=True,
        created_at=now,
        updated_at=now,
    )

    service = MagicMock(spec=ReleaseCandidateAutomationService)
    service.get_policy = AsyncMock(return_value=policy)
    dispatcher = MagicMock()
    dispatcher.enqueue = AsyncMock()

    app = create_app()
    app.dependency_overrides[get_release_candidate_automation_service] = lambda: service
    app.dependency_overrides[get_release_candidate_automation_task_dispatcher] = (
        lambda: dispatcher
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            f"/api/animes/{anime.id}/release-automation/run",
            json={},
        )

    assert response.status_code == 409
    dispatcher.enqueue.assert_not_awaited()


@pytest.mark.anyio
async def test_accept_candidate_creates_episode_and_marks_candidate_accepted() -> None:
    anime = make_anime()
    candidate = make_candidate(anime.id)
    candidate.status = "accepted"
    episode = anime.episodes[0] if anime.episodes else None
    if episode is None:
        from animedownloader_anime import Episode

        episode = Episode(
            id=uuid7(),
            anime_id=anime.id,
            episode_number=1,
            title="Episode 1",
            source="nyaa",
            source_id=candidate.source_id,
            source_title=candidate.source_title,
            source_url=candidate.page_url,
            torrent_url=candidate.torrent_url,
            size=candidate.size,
            seeders=candidate.seeders,
            leechers=candidate.leechers,
            downloads=candidate.downloads,
            info_hash=candidate.info_hash,
            download_status="not_started",
            conversion_status="not_started",
            created_at=datetime(2026, 9, 26, tzinfo=UTC),
            updated_at=datetime(2026, 9, 26, tzinfo=UTC),
        )

    service = MagicMock(spec=ReleaseDiscoveryCandidateAcceptanceService)
    service.accept = AsyncMock(
        return_value=ReleaseDiscoveryCandidateAcceptanceResult(
            status=EpisodeIngestionStatus.CREATED,
            candidate=candidate,
            episode=episode,
            existing_episode=None,
        ),
    )

    app = create_app()
    app.dependency_overrides[get_release_discovery_candidate_acceptance_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            f"/api/release-discovery/candidates/{candidate.id}/accept",
            json={},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "created"
    assert payload["candidate"]["status"] == "accepted"
    assert payload["episode"]["id"] == str(episode.id)
    service.accept.assert_awaited_once_with(candidate.id, replace_episode_id=None)


@pytest.mark.anyio
async def test_accept_candidate_forwards_explicit_replacement_target() -> None:
    anime = make_anime()
    candidate = make_candidate(anime.id)
    candidate.status = "accepted"
    from animedownloader_anime import Episode

    episode = Episode(
        id=uuid7(),
        anime_id=anime.id,
        episode_number=candidate.episode_number or 1,
        title="Existing Episode",
        source="nyaa",
        source_id="old",
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
        created_at=datetime(2026, 9, 26, tzinfo=UTC),
        updated_at=datetime(2026, 9, 26, tzinfo=UTC),
    )
    service = MagicMock(spec=ReleaseDiscoveryCandidateAcceptanceService)
    service.accept = AsyncMock(
        return_value=ReleaseDiscoveryCandidateAcceptanceResult(
            status=EpisodeIngestionStatus.REPLACED,
            candidate=candidate,
            episode=episode,
            existing_episode=None,
        ),
    )

    app = create_app()
    app.dependency_overrides[get_release_discovery_candidate_acceptance_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            f"/api/release-discovery/candidates/{candidate.id}/accept",
            json={"replace_episode_id": str(episode.id)},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "replaced"
    service.accept.assert_awaited_once_with(
        candidate.id,
        replace_episode_id=episode.id,
    )
