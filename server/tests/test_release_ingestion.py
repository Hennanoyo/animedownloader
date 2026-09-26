from datetime import UTC, datetime, time
from typing import cast
from uuid import UUID, uuid7

import pytest
from animedownloader_anime import Anime, AnimeNotFoundError, Episode
from animedownloader_api.release_ingestion import (
    EpisodeIngestionService,
    ReleaseDoesNotMatchAnimeError,
    ReleaseNotActionableError,
)
from animedownloader_releases import EpisodeIngestionStatus, ParsedRelease, ParseStatus, Release
from sqlalchemy.ext.asyncio import AsyncSession


class FakeSession:
    def __init__(self, scalar_results: list[object | None]) -> None:
        self.scalar_results = scalar_results
        self.added: list[object] = []
        self.flushed = False
        self.refreshed: list[object] = []

    def begin(self) -> FakeSession:
        return self

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def scalar(self, _statement: object) -> object | None:
        if not self.scalar_results:
            return None
        return self.scalar_results.pop(0)

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushed = True

    async def refresh(self, value: object) -> None:
        self.refreshed.append(value)


def _release(
    *,
    release_id: str = "release-8",
    title: str = "[ExampleSubs] Frieren - 08 [1080p].mkv",
    seeders: int = 10,
) -> Release:
    return Release(
        source="nyaa",
        id=release_id,
        title=title,
        page_url="https://nyaa.si/view/8",
        torrent_url="https://nyaa.si/download/8.torrent",
        published_at=datetime(2026, 9, 25, tzinfo=UTC),
        size="1.2 GiB",
        seeders=seeders,
        leechers=1,
        downloads=20,
        info_hash="hash-8",
    )


def _parsed(
    *,
    status: ParseStatus = ParseStatus.PARSED,
    series_title: str | None = "Frieren",
    episode_number: int | None = 8,
    episode_title: str | None = None,
) -> ParsedRelease:
    return ParsedRelease(
        provider_source="nyaa",
        source_id="release-8",
        original_title="raw",
        normalized_title="raw",
        release_group="ExampleSubs",
        series_title=series_title,
        episode_number=episode_number,
        episode_title=episode_title,
        season_number=None,
        resolution="1080p",
        source="WEB",
        video_codec="HEVC",
        audio_codec="AAC",
        bit_depth=10,
        status=status,
    )


def _anime() -> Anime:
    return Anime(
        id=uuid7(),
        title="Frieren: Beyond Journey's End",
        titles={"romaji": "Frieren"},
        year=2026,
        season="fall",
        weekday="friday",
        air_time=time(23),
        timezone="Asia/Tokyo",
    )


def _episode(anime_id: UUID, *, title: str = "User title") -> Episode:
    now = datetime(2026, 9, 25, tzinfo=UTC)
    return Episode(
        id=uuid7(),
        anime_id=anime_id,
        episode_number=8,
        title=title,
        source="nyaa",
        source_id="release-8",
        source_title="old",
        source_url="https://nyaa.si/view/old",
        torrent_url="https://nyaa.si/download/old.torrent",
        size="1 GiB",
        seeders=1,
        leechers=1,
        downloads=1,
        info_hash="hash-8",
        download_status="completed",
        conversion_status="completed",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_ingestion_creates_new_episode_without_download_job() -> None:
    anime = _anime()
    session = FakeSession([anime, None, None])
    service = EpisodeIngestionService(cast(AsyncSession, session))

    result = await service.ingest(
        anime_id=anime.id,
        release=_release(),
        parsed=_parsed(episode_title="Departure"),
    )

    assert result.status == EpisodeIngestionStatus.CREATED
    assert result.episode is not None
    assert result.episode.title == "Departure"
    assert result.episode.episode_number == 8
    assert result.episode.download_status == "not_started"
    assert result.episode.conversion_status == "not_started"
    assert result.episode.release_group_id is None
    assert len(session.added) == 1
    assert session.refreshed == [result.episode]


@pytest.mark.anyio
async def test_same_release_is_idempotent_and_preserves_user_state() -> None:
    anime = _anime()
    episode = _episode(anime.id)
    session = FakeSession([anime, episode])
    service = EpisodeIngestionService(cast(AsyncSession, session))

    result = await service.ingest(
        anime_id=anime.id,
        release=_release(seeders=99),
        parsed=_parsed(episode_title="New parsed title"),
    )

    assert result.status == EpisodeIngestionStatus.IDEMPOTENT
    assert result.episode is episode
    assert episode.title == "User title"
    assert episode.download_status == "completed"
    assert episode.conversion_status == "completed"
    assert episode.seeders == 99
    assert episode.source_title == "[ExampleSubs] Frieren - 08 [1080p].mkv"
    assert episode.release_group_id is None
    assert session.added == []


@pytest.mark.anyio
async def test_different_release_same_episode_returns_replacement_candidate() -> None:
    anime = _anime()
    existing = _episode(anime.id)
    session = FakeSession([anime, None, existing])
    service = EpisodeIngestionService(cast(AsyncSession, session))

    result = await service.ingest(
        anime_id=anime.id,
        release=_release(release_id="release-9"),
        parsed=_parsed(),
    )

    assert result.status == EpisodeIngestionStatus.REPLACEMENT_CANDIDATE
    assert result.episode is None
    assert result.existing_episode is existing
    assert session.added == []
    assert existing.source_id == "release-8"


@pytest.mark.anyio
async def test_mismatched_series_is_rejected() -> None:
    anime = _anime()
    session = FakeSession([anime])
    service = EpisodeIngestionService(cast(AsyncSession, session))

    with pytest.raises(ReleaseDoesNotMatchAnimeError):
        await service.ingest(
            anime_id=anime.id,
            release=_release(),
            parsed=_parsed(series_title="Bocchi the Rock"),
        )


@pytest.mark.anyio
async def test_missing_anime_is_rejected() -> None:
    anime_id = uuid7()
    session = FakeSession([None])
    service = EpisodeIngestionService(cast(AsyncSession, session))

    with pytest.raises(AnimeNotFoundError):
        await service.ingest(
            anime_id=anime_id,
            release=_release(),
            parsed=_parsed(),
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "series_title", "episode_number"),
    [
        (ParseStatus.AMBIGUOUS, "Frieren", 8),
        (ParseStatus.PARSED, None, 8),
        (ParseStatus.PARSED, "Frieren", None),
    ],
)
async def test_non_actionable_release_is_rejected(
    status: ParseStatus,
    series_title: str | None,
    episode_number: int | None,
) -> None:
    anime = _anime()
    session = FakeSession([anime])
    service = EpisodeIngestionService(cast(AsyncSession, session))

    with pytest.raises(ReleaseNotActionableError):
        await service.ingest(
            anime_id=anime.id,
            release=_release(),
            parsed=_parsed(
                status=status,
                series_title=series_title,
                episode_number=episode_number,
            ),
        )


@pytest.mark.anyio
async def test_ingestion_persists_known_release_group() -> None:
    anime = _anime()
    release_group_id = uuid7()
    session = FakeSession([anime, None, release_group_id, None])
    service = EpisodeIngestionService(cast(AsyncSession, session))

    result = await service.ingest(
        anime_id=anime.id,
        release=_release(),
        parsed=_parsed(),
    )

    assert result.status == EpisodeIngestionStatus.CREATED
    assert result.episode is not None
    assert result.episode.release_group_id == release_group_id


@pytest.mark.anyio
async def test_idempotent_ingestion_updates_known_release_group_without_resetting_state() -> None:
    anime = _anime()
    episode = _episode(anime.id)
    release_group_id = uuid7()
    session = FakeSession([anime, episode, release_group_id])
    service = EpisodeIngestionService(cast(AsyncSession, session))

    result = await service.ingest(
        anime_id=anime.id,
        release=_release(seeders=77),
        parsed=_parsed(episode_title="Replacement title"),
    )

    assert result.status == EpisodeIngestionStatus.IDEMPOTENT
    assert result.episode is episode
    assert episode.release_group_id == release_group_id
    assert episode.title == "User title"
    assert episode.download_status == "completed"


@pytest.mark.anyio
async def test_replace_release_requires_no_download_history_and_preserves_episode_state() -> None:
    anime = _anime()
    existing = _episode(anime.id, title="Keep this title")
    existing.download_status = "not_started"
    existing.conversion_status = "not_started"
    release_group_id = uuid7()
    session = FakeSession(
        [existing, anime, None, None, None, release_group_id],
    )
    service = EpisodeIngestionService(cast(AsyncSession, session))

    result = await service.replace(
        episode_id=existing.id,
        release=_release(release_id="release-9", seeders=55),
        parsed=_parsed(episode_title="Parsed title"),
    )

    assert result.status == EpisodeIngestionStatus.REPLACED
    assert result.episode is existing
    assert result.existing_episode is None
    assert existing.title == "Keep this title"
    assert existing.source_id == "release-9"
    assert existing.seeders == 55
    assert existing.release_group_id == release_group_id
    assert existing.download_status == "not_started"
    assert existing.conversion_status == "not_started"
    assert session.added == []


@pytest.mark.anyio
async def test_replace_release_rejects_existing_download_history() -> None:
    anime = _anime()
    existing = _episode(anime.id, title="Keep this title")
    session = FakeSession([existing, anime, uuid7()])
    service = EpisodeIngestionService(cast(AsyncSession, session))

    from animedownloader_api.release_ingestion import ReleaseReplacementConflictError

    with pytest.raises(ReleaseReplacementConflictError):
        await service.replace(
            episode_id=existing.id,
            release=_release(release_id="release-9"),
            parsed=_parsed(),
        )
