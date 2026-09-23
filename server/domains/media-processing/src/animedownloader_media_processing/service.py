from uuid import UUID

from animedownloader_anime import Episode, EpisodeNotFoundError
from animedownloader_download import (
    DownloadJob,
    DownloadJobNotFoundError,
    DownloadJobStatus,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import MediaProcessingJobStatus
from .exceptions import MediaProcessingJobNotFoundError
from .models import MediaProcessingJob
from .repository import MediaProcessingJobRepository


class MediaProcessingJobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.jobs = MediaProcessingJobRepository(session)

    async def get_job(self, job_id: UUID) -> MediaProcessingJob:
        job = await self.jobs.get(job_id)
        if job is None:
            raise MediaProcessingJobNotFoundError(job_id)
        return job

    async def get_latest_job(self, episode_id: UUID) -> MediaProcessingJob | None:
        return await self.jobs.get_latest_for_episode(episode_id)

    async def create_job(
        self,
        episode_id: UUID,
        download_job_id: UUID,
    ) -> MediaProcessingJob:
        await self.session.rollback()
        async with self.session.begin():
            episode = await self.session.get(Episode, episode_id)
            if episode is None:
                raise EpisodeNotFoundError(episode_id)

            download_job = await self.session.get(DownloadJob, download_job_id)
            if download_job is None:
                raise DownloadJobNotFoundError(download_job_id)

            if download_job.episode_id != episode_id:
                raise ValueError("Download job does not belong to episode")

            if download_job.job_status is not DownloadJobStatus.COMPLETED:
                raise ValueError("Media processing requires a completed download job")

            existing = await self.jobs.get_by_download_job(download_job_id)
            if existing is not None:
                return existing

            job = MediaProcessingJob(
                episode_id=episode_id,
                download_job_id=download_job_id,
            )
            await self.jobs.add(job)

        await self.session.refresh(job)
        return job

    async def mark_processing(self, job_id: UUID) -> MediaProcessingJob:
        return await self._transition(job_id, MediaProcessingJobStatus.PROCESSING)

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        media_path: str,
        probe_metadata: dict[str, object],
    ) -> MediaProcessingJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            job.media_path = media_path
            job.probe_metadata = probe_metadata
            job.transition_to(MediaProcessingJobStatus.COMPLETED)

        await self.session.refresh(job)
        return job

    async def mark_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
    ) -> MediaProcessingJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            job.transition_to(MediaProcessingJobStatus.FAILED)
            job.error_message = error_message[:2000]

        await self.session.refresh(job)
        return job

    async def retry_job(self, job_id: UUID) -> MediaProcessingJob:
        return await self._transition(job_id, MediaProcessingJobStatus.PENDING)

    async def _transition(
        self,
        job_id: UUID,
        status: MediaProcessingJobStatus,
    ) -> MediaProcessingJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            job.transition_to(status)

        await self.session.refresh(job)
        return job
