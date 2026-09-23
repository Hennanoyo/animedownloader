from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from animedownloader_anime import Episode
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
        poll_interval: float = 3.0,
        discovery_timeout: float = 60.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._state = state
        self._torrent_client = torrent_client
        self._download_root = download_root
        self._poll_interval = poll_interval
        self._discovery_timeout = discovery_timeout
        self._sleep = sleep

    async def run(self, job_id: UUID) -> None:
        try:
            context = await self._state.load(job_id)
            while context.status is DownloadJobStatus.PAUSED:
                await self._sleep(self._poll_interval)
                context = await self._state.load(job_id)

            if context.status in {
                DownloadJobStatus.COMPLETED,
                DownloadJobStatus.FAILED,
                DownloadJobStatus.CANCELLED,
            }:
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
                    return

                info = await self._torrent_client.get(torrent.id)
                if info is None:
                    raise DownloadExecutionError(
                        f"Torrent disappeared from qBittorrent: {torrent.id}"
                    )

                if context.status is DownloadJobStatus.PAUSED:
                    if info.status is not TorrentStatus.PAUSED:
                        try:
                            await self._torrent_client.pause(info.id)
                        except Exception:
                            logger.exception(
                                "Failed to pause qBittorrent torrent %s",
                                info.id,
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

                await self._state.update_progress(
                    job_id,
                    downloaded_bytes=info.downloaded_bytes,
                    total_bytes=info.total_bytes,
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
                    return

                await self._sleep(self._poll_interval)
        except Exception as exc:
            with suppress(Exception):
                await self._state.mark_failed(
                    job_id,
                    error_message=_format_error(exc),
                )
            raise

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
