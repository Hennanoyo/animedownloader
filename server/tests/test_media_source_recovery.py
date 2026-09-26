from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid7

import pytest

from animedownloader_database import Database
from animedownloader_media_processing import MediaProcessingJobStatus
from animedownloader_worker import source_recovery
from animedownloader_worker.media_source import (
    MediaSourceStatus,
    describe_media_source,
    resolve_media_source,
)


def test_resolve_media_source_reports_missing_directory(tmp_path: Path) -> None:
    resolution = resolve_media_source(tmp_path / "missing")

    assert resolution.status is MediaSourceStatus.MISSING_DIRECTORY
    assert resolution.path is None
    assert not resolution.is_ready


def test_resolve_media_source_reports_no_media(tmp_path: Path) -> None:
    root = tmp_path / "download"
    root.mkdir()
    (root / "readme.txt").write_text("not media")

    resolution = resolve_media_source(root)

    assert resolution.status is MediaSourceStatus.NO_MEDIA
    assert resolution.candidates == ()
    assert "No supported media file found" in describe_media_source(resolution)


def test_resolve_media_source_finds_nested_media_file(tmp_path: Path) -> None:
    root = tmp_path / "download"
    nested = root / "release"
    nested.mkdir(parents=True)
    media = nested / "episode.MKV"
    media.touch()

    resolution = resolve_media_source(root)

    assert resolution.status is MediaSourceStatus.FOUND
    assert resolution.path == media
    assert resolution.is_ready


def test_resolve_media_source_reports_ambiguous_media(tmp_path: Path) -> None:
    root = tmp_path / "download"
    root.mkdir()
    first = root / "episode-1.mkv"
    second = root / "episode-2.mp4"
    first.touch()
    second.touch()

    resolution = resolve_media_source(root)

    assert resolution.status is MediaSourceStatus.AMBIGUOUS
    assert resolution.path is None
    assert resolution.candidates == (first, second)
    assert "found 2" in describe_media_source(resolution)


class _FakeResult:
    def __init__(self, values: list[UUID]) -> None:
        self._values = values

    def __iter__(self):
        return iter(self._values)


class _FakeSession:
    def __init__(self, values: list[UUID]) -> None:
        self.values = values

    async def scalars(self, _statement: object) -> _FakeResult:
        return _FakeResult(self.values)


class _FakeDatabase:
    def __init__(self, session_values: list[UUID]) -> None:
        self.session_values = session_values

    @asynccontextmanager
    async def _session(self):
        yield _FakeSession(self.session_values)

    @property
    def session_factory(self):
        return self._session


@pytest.mark.anyio
async def test_recover_completed_download_handoffs_enqueues_only_resolved_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready_job_id = uuid7()
    missing_job_id = uuid7()

    ready_root = tmp_path / str(ready_job_id)
    ready_root.mkdir()
    (ready_root / "episode.mkv").touch()

    calls: list[UUID] = []

    class FakeService:
        def __init__(self, _session: object) -> None:
            pass

        async def ensure_for_download_job(
            self,
            download_job_id: UUID,
        ) -> tuple[SimpleNamespace, bool]:
            return SimpleNamespace(
                id=download_job_id,
                job_status=MediaProcessingJobStatus.PENDING,
                status="pending",
            ), True

    monkeypatch.setattr(
        source_recovery,
        "MediaProcessingJobService",
        FakeService,
    )

    async def enqueue(job_id: UUID) -> None:
        calls.append(job_id)

    database = cast(
        Database,
        _FakeDatabase([ready_job_id, missing_job_id]),
    )

    recovered, unresolved = await source_recovery.recover_completed_download_handoffs(
        database,
        download_root=tmp_path,
        enqueue_media_processing=enqueue,
    )

    assert recovered == 1
    assert unresolved == 1
    assert calls == [ready_job_id]
