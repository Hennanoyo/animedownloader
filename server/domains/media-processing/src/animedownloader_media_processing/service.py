from uuid import UUID

from animedownloader_anime import Episode, EpisodeNotFoundError
from animedownloader_download import (
    DownloadJob,
    DownloadJobNotFoundError,
    DownloadJobStatus,
)
from sqlalchemy import select
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

    async def get_active_jobs(self) -> list[MediaProcessingJob]:
        return await self.jobs.get_active_processing_jobs()

    async def get_job_by_download_job(
        self,
        download_job_id: UUID,
    ) -> MediaProcessingJob | None:
        return await self.jobs.get_by_download_job(download_job_id)

    async def create_for_download_job(
        self,
        download_job_id: UUID,
    ) -> MediaProcessingJob:
        job, _created = await self.ensure_for_download_job(download_job_id)
        return job

    async def ensure_for_download_job(
        self,
        download_job_id: UUID,
    ) -> tuple[MediaProcessingJob, bool]:
        await self.session.rollback()
        async with self.session.begin():
            download_job = await self.session.scalar(
                select(DownloadJob)
                .where(DownloadJob.id == download_job_id)
                .with_for_update(),
            )
            if download_job is None:
                raise DownloadJobNotFoundError(download_job_id)

            if download_job.job_status is not DownloadJobStatus.COMPLETED:
                raise ValueError(
                    "Media processing requires a completed download job",
                )

            existing = await self.jobs.get_by_download_job(download_job_id)
            if existing is not None:
                return existing, False

            episode = await self.session.get(Episode, download_job.episode_id)
            if episode is None:
                raise EpisodeNotFoundError(download_job.episode_id)

            job = MediaProcessingJob(
                episode_id=episode.id,
                download_job_id=download_job.id,
                download_directory=str(download_job.id),
            )
            await self.jobs.add(job)

        await self.session.refresh(job)
        return job, True

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
                download_directory=str(download_job_id),
            )
            await self.jobs.add(job)

        await self.session.refresh(job)
        return job

    async def select_source(
        self,
        job_id: UUID,
        *,
        media_path: str,
    ) -> MediaProcessingJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            if job.job_status is MediaProcessingJobStatus.PROCESSING:
                raise ValueError("Media processing is already in progress.")
            if job.job_status is MediaProcessingJobStatus.COMPLETED:
                raise ValueError("Completed media processing cannot change its source.")

            if job.job_status is MediaProcessingJobStatus.FAILED:
                job.transition_to(MediaProcessingJobStatus.PENDING)

            job.media_path = media_path

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
