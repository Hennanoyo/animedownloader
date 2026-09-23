import logging
from uuid import UUID

from animedownloader_download import DownloadJob, DownloadJobService
from animedownloader_torrent import TorrentClient, TorrentInfo, TorrentStatus

DOWNLOAD_TAG_PREFIX = "animedownloader:job-"
logger = logging.getLogger(__name__)


class DownloadControlService:
    def __init__(
        self,
        jobs: DownloadJobService,
        torrent_client: TorrentClient,
    ) -> None:
        self.jobs = jobs
        self.torrent_client = torrent_client

    async def pause(self, job_id: UUID) -> DownloadJob:
        job = await self.jobs.mark_paused(job_id)
        torrent = await self._find_torrent(job.id)
        if torrent is not None and torrent.status is not TorrentStatus.PAUSED:
            try:
                await self.torrent_client.pause(torrent.id)
            except Exception:
                logger.exception("Failed to pause qBittorrent torrent %s", torrent.id)
        return job

    async def resume(self, job_id: UUID) -> DownloadJob:
        job = await self.jobs.mark_downloading(job_id)
        torrent = await self._find_torrent(job.id)
        if torrent is not None and torrent.status is TorrentStatus.PAUSED:
            try:
                await self.torrent_client.resume(torrent.id)
            except Exception:
                logger.exception("Failed to resume qBittorrent torrent %s", torrent.id)
        return job

    async def cancel(self, job_id: UUID) -> DownloadJob:
        job = await self.jobs.mark_cancelled(job_id)
        torrent = await self._find_torrent(job.id)
        if torrent is not None:
            try:
                await self.torrent_client.remove(torrent.id, delete_files=True)
            except Exception:
                logger.exception(
                    "Failed to remove cancelled qBittorrent torrent %s",
                    torrent.id,
                )
        return job

    async def delete(self, job_id: UUID) -> None:
        job = await self.jobs.get_job(job_id)
        torrent = await self._find_torrent(job.id)
        if torrent is not None:
            await self.torrent_client.remove(torrent.id, delete_files=False)
        await self.jobs.delete_job(job_id)

    async def _find_torrent(self, job_id: UUID) -> TorrentInfo | None:
        return await self.torrent_client.find_by_tag(
            f"{DOWNLOAD_TAG_PREFIX}{job_id}",
        )
