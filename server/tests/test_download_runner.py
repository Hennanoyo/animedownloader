from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid7

import pytest
from animedownloader_download import DownloadJobStatus
from animedownloader_torrent import TorrentInfo, TorrentStatus
from animedownloader_worker.runner import (
    DOWNLOAD_TAG_PREFIX,
    DownloadContext,
    DownloadExecutionError,
    DownloadRunner,
)


@dataclass
class FakeState:
    context: DownloadContext
    transitions: list[str] = field(default_factory=lambda: list[str]())
    progress: list[tuple[int, int]] = field(
        default_factory=lambda: list[tuple[int, int]]()
    )
    completed: tuple[int, int] | None = None
    failed_message: str | None = None

    async def load(self, job_id: UUID) -> DownloadContext:
        return self.context

    async def mark_downloading(self, job_id: UUID) -> None:
        self.transitions.append("downloading")
        self.context = DownloadContext(
            status=DownloadJobStatus.DOWNLOADING,
            torrent_url=self.context.torrent_url,
        )

    async def update_progress(
        self,
        job_id: UUID,
        *,
        downloaded_bytes: int,
        total_bytes: int,
    ) -> None:
        self.progress.append((downloaded_bytes, total_bytes))

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        downloaded_bytes: int,
        total_bytes: int,
    ) -> None:
        self.completed = (downloaded_bytes, total_bytes)

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        self.failed_message = error_message


@dataclass
class FakeTorrentClient:
    torrents: list[TorrentInfo]
    added: list[tuple[str, str, tuple[str, ...]]] = field(
        default_factory=lambda: list[tuple[str, str, tuple[str, ...]]]()
    )
    info_sequence: list[TorrentInfo] = field(
        default_factory=lambda: list[TorrentInfo]()
    )

    async def find_by_tag(self, tag: str) -> TorrentInfo | None:
        if self.torrents:
            return self.torrents[-1]
        if self.added:
            return make_torrent(TorrentStatus.DOWNLOADING, 0.0, 0)
        return None

    async def add(
        self,
        source: str,
        *,
        save_path: str,
        tags: Sequence[str] = (),
    ) -> None:
        self.added.append((source, save_path, tuple(tags)))

    async def get(self, torrent_id: str) -> TorrentInfo | None:
        if self.info_sequence:
            return self.info_sequence.pop(0)
        return self.torrents[-1] if self.torrents else None

    async def remove(
        self,
        torrent_id: str,
        *,
        delete_files: bool = False,
    ) -> None:
        raise NotImplementedError


def make_torrent(status: TorrentStatus, progress: float, downloaded: int) -> TorrentInfo:
    return TorrentInfo(
        id="torrent-1",
        name="Episode One",
        status=status,
        progress=progress,
        downloaded_bytes=downloaded,
        total_bytes=1000,
        save_path="/data/downloads/job",
        tags=frozenset(),
    )


@pytest.mark.anyio
async def test_download_runner_starts_download_and_persists_completion(tmp_path: Path) -> None:
    job_id = uuid7()
    state = FakeState(
        DownloadContext(
            status=DownloadJobStatus.PENDING,
            torrent_url="https://example.com/episode.torrent",
        )
    )
    client = FakeTorrentClient(
        torrents=[],
        info_sequence=[
            make_torrent(TorrentStatus.DOWNLOADING, 0.5, 500),
            make_torrent(TorrentStatus.SEEDING, 1.0, 1000),
        ],
    )

    async def no_sleep(_: float) -> None:
        return

    runner = DownloadRunner(
        state=state,
        torrent_client=client,
        download_root=tmp_path,
        poll_interval=0,
        sleep=no_sleep,
    )
    await runner.run(job_id)

    assert state.transitions == ["downloading"]
    assert client.added == [
        (
            "https://example.com/episode.torrent",
            str(tmp_path / str(job_id)),
            (f"{DOWNLOAD_TAG_PREFIX}{job_id}",),
        )
    ]
    assert state.progress == [(500, 1000), (1000, 1000)]
    assert state.completed == (1000, 1000)
    assert (tmp_path / str(job_id)).is_dir()


@pytest.mark.anyio
async def test_download_runner_reuses_existing_torrent(tmp_path: Path) -> None:
    job_id = uuid7()
    state = FakeState(
        DownloadContext(
            status=DownloadJobStatus.DOWNLOADING,
            torrent_url="https://example.com/episode.torrent",
        )
    )
    torrent = make_torrent(TorrentStatus.SEEDING, 1.0, 1000)
    client = FakeTorrentClient(torrents=[torrent])

    runner = DownloadRunner(
        state=state,
        torrent_client=client,
        download_root=tmp_path,
    )
    await runner.run(job_id)

    assert client.added == []
    assert state.completed == (1000, 1000)


@pytest.mark.anyio
async def test_download_runner_marks_failed_on_torrent_error(tmp_path: Path) -> None:
    job_id = uuid7()
    state = FakeState(
        DownloadContext(
            status=DownloadJobStatus.DOWNLOADING,
            torrent_url="https://example.com/episode.torrent",
        )
    )
    client = FakeTorrentClient(
        torrents=[],
        info_sequence=[
            make_torrent(TorrentStatus.ERROR, 0.25, 250),
        ],
    )

    runner = DownloadRunner(
        state=state,
        torrent_client=client,
        download_root=tmp_path,
        poll_interval=0,
    )

    with pytest.raises(DownloadExecutionError, match="reported an error"):
        await runner.run(job_id)

    assert state.failed_message == "qBittorrent reported an error for torrent torrent-1"
