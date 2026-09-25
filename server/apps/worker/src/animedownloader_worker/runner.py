from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

from animedownloader_anime import Episode
from animedownloader_config import JobProgressEvent
from animedownloader_database import Database
from animedownloader_download import DownloadJobService, DownloadJobStatus
from animedownloader_torrent import TorrentClient, TorrentInfo, TorrentStatus
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

DOWNLOAD_TAG_PREFIX = "animedownloader:job-"

logger = logging.getLogger(__name__)


class DownloadExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DownloadContext:
    status: DownloadJobStatus
    torrent_url: str


class DownloadState(Protocol):
    async def load(self, job_id: UUID) -> DownloadContext: ...

    async def mark_downloading(self, job_id: UUID) -> None: ...

    async def update_progress(
        self,
        job_id: UUID,
        *,
        downloaded_bytes: int,
        total_bytes: int,
    ) -> None: ...

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        downloaded_bytes: int,
        total_bytes: int,
    ) -> None: ...

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None: ...


class PostgresDownloadState:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, job_id: UUID) -> DownloadContext:
        async with self._session_factory() as session:
            service = DownloadJobService(session)
            job = await service.get_job(job_id)
            episode = await session.get(Episode, job.episode_id)
            if episode is None:
                raise DownloadExecutionError(f"Episode not found for download job: {job_id}")
            return DownloadContext(
                status=job.job_status,
                torrent_url=episode.torrent_url,
            )

    async def mark_downloading(self, job_id: UUID) -> None:
        async with self._session_factory() as session:
            await DownloadJobService(session).mark_downloading(job_id)

    async def update_progress(
        self,
        job_id: UUID,
        *,
        downloaded_bytes: int,
        total_bytes: int,
    ) -> None:
        async with self._session_factory() as session:
            await DownloadJobService(session).update_progress(
                job_id,
                downloaded_bytes=downloaded_bytes,
                total_bytes=total_bytes,
            )

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        downloaded_bytes: int,
        total_bytes: int,
    ) -> None:
        async with self._session_factory() as session:
            await DownloadJobService(session).mark_completed(
                job_id,
                downloaded_bytes=downloaded_bytes,
                total_bytes=total_bytes,
            )

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        async with self._session_factory() as session:
            await DownloadJobService(session).mark_failed(
                job_id,
                error_message=error_message,
            )


class DownloadRunner:
    def __init__(
        self,
        *,
        state: DownloadState,
        torrent_client: TorrentClient,
        download_root: Path,
        on_completed: Callable[[UUID], Awaitable[None]] | None = None,
        on_progress: Callable[[JobProgressEvent], Awaitable[None]] | None = None,
        poll_interval: float = 3.0,
        progress_checkpoint_interval: float = 15.0,
        discovery_timeout: float = 60.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._state = state
        self._torrent_client = torrent_client
        self._download_root = download_root
        self._on_completed = on_completed
        self._on_progress = on_progress
        self._poll_interval = poll_interval
        self._progress_checkpoint_interval = progress_checkpoint_interval
        self._discovery_timeout = discovery_timeout
        self._sleep = sleep

    async def run(self, job_id: UUID) -> None:
        last_checkpoint_at: float | None = None
        last_checkpoint_total_bytes: int | None = None
        last_downloaded_bytes = 0
        last_total_bytes = 0
        last_progress_percent = 0.0
        try:
            context = await self._state.load(job_id)
            while context.status is DownloadJobStatus.PAUSED:
                await self._publish_progress(
                    job_id,
                    status=DownloadJobStatus.PAUSED,
                    downloaded_bytes=None,
                    total_bytes=None,
                    progress_percent=None,
                )
                await self._sleep(self._poll_interval)
                context = await self._state.load(job_id)

            if context.status in {
                DownloadJobStatus.COMPLETED,
                DownloadJobStatus.FAILED,
                DownloadJobStatus.CANCELLED,
            }:
                await self._publish_progress(
                    job_id,
                    status=context.status,
                    downloaded_bytes=None,
                    total_bytes=None,
                    progress_percent=None,
                )
                return

            if context.status is DownloadJobStatus.PENDING:
                await self._state.mark_downloading(job_id)

            save_path = self._download_root / str(job_id)
            tag = f"{DOWNLOAD_TAG_PREFIX}{job_id}"

            torrent = await self._torrent_client.find_by_tag(tag)
            if torrent is None:
                await self._torrent_client.add(
                    context.torrent_url,
                    save_path=str(save_path),
                    tags=(tag,),
                )
                torrent = await self._wait_for_torrent(job_id, tag)
                if torrent is None:
                    return

            while True:
                context = await self._state.load(job_id)
                if context.status in {
                    DownloadJobStatus.COMPLETED,
                    DownloadJobStatus.FAILED,
                    DownloadJobStatus.CANCELLED,
                }:
                    await self._publish_progress(
                        job_id,
                        status=context.status,
                        downloaded_bytes=last_downloaded_bytes,
                        total_bytes=last_total_bytes,
                        progress_percent=last_progress_percent,
                    )
                    return

                info = await self._torrent_client.get(torrent.id)
                if info is None:
                    raise DownloadExecutionError(
                        f"Torrent disappeared from qBittorrent: {torrent.id}"
                    )

                last_downloaded_bytes = info.downloaded_bytes
                last_total_bytes = info.total_bytes
                last_progress_percent = max(0.0, min(info.progress * 100.0, 100.0))

                if context.status is DownloadJobStatus.PAUSED:
                    if info.status is not TorrentStatus.PAUSED:
                        try:
                            await self._torrent_client.pause(info.id)
                        except Exception:
                            logger.exception(
                                "Failed to pause qBittorrent torrent %s",
                                info.id,
                            )
                    await self._publish_progress(
                        job_id,
                        status=DownloadJobStatus.PAUSED,
                        downloaded_bytes=info.downloaded_bytes,
                        total_bytes=info.total_bytes,
                        progress_percent=last_progress_percent,
                    )
                    await self._sleep(self._poll_interval)
                    continue

                if info.status is TorrentStatus.PAUSED:
                    try:
                        await self._torrent_client.resume(info.id)
                    except Exception:
                        logger.exception(
                            "Failed to resume qBittorrent torrent %s",
                            info.id,
                        )
                        await self._sleep(self._poll_interval)
                        continue

                now = asyncio.get_running_loop().time()
                if (
                    last_checkpoint_at is None
                    or now - last_checkpoint_at >= self._progress_checkpoint_interval
                    or last_checkpoint_total_bytes != info.total_bytes
                ):
                    await self._state.update_progress(
                        job_id,
                        downloaded_bytes=info.downloaded_bytes,
                        total_bytes=info.total_bytes,
                    )
                    last_checkpoint_at = now
                    last_checkpoint_total_bytes = info.total_bytes

                await self._publish_progress(
                    job_id,
                    status=DownloadJobStatus.DOWNLOADING,
                    downloaded_bytes=info.downloaded_bytes,
                    total_bytes=info.total_bytes,
                    progress_percent=last_progress_percent,
                )

                if info.status is TorrentStatus.ERROR:
                    raise DownloadExecutionError(
                        f"qBittorrent reported an error for torrent {info.id}"
                    )

                if info.is_complete:
                    await self._state.mark_completed(
                        job_id,
                        downloaded_bytes=info.downloaded_bytes,
                        total_bytes=info.total_bytes,
                    )
                    await self._publish_progress(
                        job_id,
                        status=DownloadJobStatus.COMPLETED,
                        downloaded_bytes=info.downloaded_bytes,
                        total_bytes=info.total_bytes,
                        progress_percent=100.0,
                    )
                    try:
                        await self._torrent_client.remove(
                            info.id,
                            delete_files=False,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to remove completed qBittorrent torrent %s",
                            info.id,
                        )

                    if self._on_completed is not None:
                        try:
                            await self._on_completed(job_id)
                        except Exception:
                            logger.exception(
                                "Failed to enqueue media processing job for download %s",
                                job_id,
                            )
                    return

                await self._sleep(self._poll_interval)
        except Exception as exc:
            error_message = _format_error(exc)
            with suppress(Exception):
                await self._state.mark_failed(
                    job_id,
                    error_message=error_message,
                )
            await self._publish_progress(
                job_id,
                status=DownloadJobStatus.FAILED,
                downloaded_bytes=last_downloaded_bytes,
                total_bytes=last_total_bytes,
                progress_percent=last_progress_percent,
                error_message=error_message,
            )
            raise

    async def _publish_progress(
        self,
        job_id: UUID,
        *,
        status: DownloadJobStatus,
        downloaded_bytes: int | None,
        total_bytes: int | None,
        progress_percent: float | None,
        error_message: str | None = None,
    ) -> None:
        if self._on_progress is None:
            return
        event = JobProgressEvent(
            job_type="download",
            job_id=job_id,
            status=status,
            progress_percent=progress_percent,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            error_message=error_message,
            emitted_at=datetime.now(UTC),
        )
        try:
            await self._on_progress(event)
        except Exception:
            logger.exception(
                "Failed to publish progress event for download %s",
                job_id,
            )

    async def _wait_for_torrent(
        self,
        job_id: UUID,
        tag: str,
    ) -> TorrentInfo | None:
        deadline = asyncio.get_running_loop().time() + self._discovery_timeout
        while True:
            context = await self._state.load(job_id)
            if context.status in {
                DownloadJobStatus.COMPLETED,
                DownloadJobStatus.FAILED,
                DownloadJobStatus.CANCELLED,
            }:
                return None

            torrent = await self._torrent_client.find_by_tag(tag)
            if torrent is not None:
                return torrent
            if asyncio.get_running_loop().time() >= deadline:
                raise DownloadExecutionError(
                    f"Timed out waiting for qBittorrent to register torrent with tag {tag}"
                )
            await self._sleep(self._poll_interval)


def _format_error(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    return message[:2000]


def create_download_state(database: Database) -> PostgresDownloadState:
    return PostgresDownloadState(database.session_factory)
