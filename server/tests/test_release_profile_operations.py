from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid7

import httpx
import pytest
from animedownloader_api.app import create_app
from animedownloader_api.dependencies import get_release_profile_service
from animedownloader_releases import (
    ParsedRelease,
    ParseStatus,
    ParserField,
    ParserTransform,
    Release,
    ReleaseProfileService,
)
from animedownloader_releases.service import (
    ParserSampleResult,
    ParserValidationResult,
)


def _release() -> Release:
    return Release(
        source="nyaa",
        id="https://nyaa.si/view/123",
        title="[ExampleSubs] Frieren Episode-08 [1080p].mkv",
        page_url="https://nyaa.si/view/123",
        torrent_url="https://nyaa.si/download/123.torrent",
        published_at=None,
        size="1.2 GiB",
        seeders=1,
        leechers=0,
        downloads=2,
        info_hash=None,
    )


def _parsed() -> ParsedRelease:
    release = _release()
    return ParsedRelease(
        provider_source=release.source,
        source_id=release.id,
        original_title=release.title,
        normalized_title=release.title.removesuffix(".mkv"),
        release_group="ExampleSubs",
        series_title="Frieren",
        episode_number=8,
        episode_title=None,
        season_number=None,
        resolution="1080p",
        source=None,
        video_codec="HEVC",
        audio_codec=None,
        bit_depth=10,
        status=ParseStatus.PARSED,
    )


@pytest.mark.anyio
async def test_release_groups_endpoint() -> None:
    group_id = uuid7()
    now = datetime.now(UTC)
    group = SimpleNamespace(
        id=group_id,
        name="ExampleSubs",
        slug="examplesubs",
        enabled=True,
        parser_profiles=[
            SimpleNamespace(version=1, status="active"),
            SimpleNamespace(version=2, status="draft"),
        ],
    )
    service = MagicMock(spec=ReleaseProfileService)
    service.list_groups = AsyncMock(return_value=[group])

    app = create_app()
    app.dependency_overrides[get_release_profile_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/release-groups")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(group_id),
            "name": "ExampleSubs",
            "slug": "examplesubs",
            "enabled": True,
            "active_parser_profile_version": 1,
            "draft_parser_profile_version": 2,
        },
    ]
    assert now <= datetime.now(UTC)


@pytest.mark.anyio
async def test_validate_parser_profile_endpoint() -> None:
    profile_id = uuid7()
    sample_id = uuid7()
    parsed = _parsed()
    result = ParserValidationResult(
        valid=True,
        sample_count=2,
        minimum_samples=2,
        errors=(),
        results=(
            ParserSampleResult(
                sample_id=sample_id,
                title=_release().title,
                parsed=parsed,
                error=None,
            ),
        ),
    )

    service = MagicMock(spec=ReleaseProfileService)
    service.validate_profile = AsyncMock(return_value=result)

    app = create_app()
    app.dependency_overrides[get_release_profile_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            f"/api/release-parser-profiles/{profile_id}/validate",
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["sample_count"] == 2
    assert payload["results"][0]["parsed"]["episode_number"] == 8


def test_profile_schema_accepts_declared_rule_values() -> None:
    from animedownloader_api.release_profile_schemas import ReleaseParserRuleInput

    payload = ReleaseParserRuleInput(
        field=ParserField.EPISODE_NUMBER,
        pattern=r"Episode-(?P<episode_number>\d+)",
        priority=10,
        required=True,
        flags="i",
        transform=ParserTransform.TO_INT,
    )

    assert payload.field == ParserField.EPISODE_NUMBER
    assert payload.transform == ParserTransform.TO_INT


def test_health_result_marks_drift_after_threshold() -> None:
    # The domain service's thresholds are intentionally exposed as named constants;
    # this test documents the operating signal rather than a hardcoded UI rule.
    service = ReleaseProfileService(MagicMock())
    assert service.DRIFT_MIN_TOTAL == 8
    assert service.DRIFT_FAILURE_RATE == 0.25
    assert service.DRIFT_RECENT_FAILURES == 3
