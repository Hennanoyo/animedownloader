from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid7

from animedownloader_anime import AnimeReleasePreference
from animedownloader_api.release_candidate_automation import (
    AnimeReleaseAutomationPolicy,
    ReleaseCandidateAutomationService,
)
from animedownloader_api.release_candidates import ReleaseDiscoveryCandidate
from animedownloader_releases import AnimeMatchStatus


def make_candidate(**overrides: object) -> ReleaseDiscoveryCandidate:
    now = datetime(2026, 9, 26, tzinfo=UTC)
    values: dict[str, object] = {
        "id": uuid7(),
        "anime_id": uuid7(),
        "provider_source": "nyaa",
        "source_id": "release-1",
        "source_title": "[ExampleSubs] Anime - 01 [1080p][HEVC]",
        "page_url": "https://nyaa.si/view/1",
        "torrent_url": "https://nyaa.si/download/1.torrent",
        "normalized_title": "anime 01",
        "release_group": "ExampleSubs",
        "series_title": "Anime",
        "episode_number": 1,
        "resolution": "1080p",
        "source": "WEB",
        "video_codec": "HEVC",
        "audio_codec": "AAC",
        "bit_depth": 10,
        "parse_status": "parsed",
        "parse_warnings": [],
        "failed_required_fields": [],
        "normalized_series_title": "anime",
        "match_status": AnimeMatchStatus.MATCHED.value,
        "match_candidates": [],
        "ranking_score": 160,
        "ranking_reasons": ["Preferred resolution"],
        "status": "new",
        "first_seen_at": now,
        "last_seen_at": now,
        "reviewed_at": None,
        "automation_status": "idle",
        "automation_claimed_at": None,
        "automation_completed_at": None,
        "automation_error": None,
    }
    values.update(overrides)
    return ReleaseDiscoveryCandidate(**values)


def make_policy(**overrides: object) -> AnimeReleaseAutomationPolicy:
    values: dict[str, object] = {
        "anime_id": uuid7(),
        "enabled": True,
        "min_ranking_score": 100,
        "require_preference_match": True,
    }
    values.update(overrides)
    return AnimeReleaseAutomationPolicy(**values)


def test_disabled_policy_never_selects_candidate() -> None:
    result = ReleaseCandidateAutomationService._evaluate(
        make_candidate(),
        make_policy(enabled=False),
        None,
        None,
    )

    assert result.eligible is False
    assert result.reasons == ("Automation is disabled",)


def test_automation_requires_preferences_by_default() -> None:
    result = ReleaseCandidateAutomationService._evaluate(
        make_candidate(),
        make_policy(),
        None,
        None,
    )

    assert result.eligible is False
    assert "No release preference is configured" in result.reasons


def test_all_configured_preferences_must_match() -> None:
    preference = AnimeReleasePreference(
        anime_id=uuid7(),
        release_group_id=None,
        resolution="1080p",
        video_codec="HEVC",
        source="WEB",
    )

    result = ReleaseCandidateAutomationService._evaluate(
        make_candidate(),
        make_policy(),
        preference,
        None,
    )

    assert result.eligible is True
    assert result.reasons == ("Candidate satisfies the automatic download policy",)


def test_preference_mismatch_blocks_automatic_selection() -> None:
    preference = AnimeReleasePreference(
        anime_id=uuid7(),
        release_group_id=None,
        resolution="720p",
        video_codec="HEVC",
        source="WEB",
    )

    result = ReleaseCandidateAutomationService._evaluate(
        make_candidate(),
        make_policy(),
        preference,
        None,
    )

    assert result.eligible is False
    assert "Preferred resolution does not match" in result.reasons


def test_non_actionable_or_ambiguous_candidates_are_blocked() -> None:
    non_actionable = make_candidate(parse_status="ambiguous", episode_number=None)
    ambiguous = make_candidate(match_status=AnimeMatchStatus.AMBIGUOUS.value)

    non_actionable_result = ReleaseCandidateAutomationService._evaluate(
        non_actionable,
        make_policy(require_preference_match=False),
        None,
        None,
    )
    ambiguous_result = ReleaseCandidateAutomationService._evaluate(
        ambiguous,
        make_policy(require_preference_match=False),
        None,
        None,
    )

    assert non_actionable_result.eligible is False
    assert ambiguous_result.eligible is False


def test_score_threshold_is_applied_after_candidate_ranking() -> None:
    result = ReleaseCandidateAutomationService._evaluate(
        make_candidate(ranking_score=99),
        make_policy(require_preference_match=False, min_ranking_score=100),
        None,
        None,
    )

    assert result.eligible is False
    assert "Ranking score 99 is below the minimum 100" in result.reasons
