from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import MediaProcessingJob


class MediaProcessingJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, job_id: UUID) -> MediaProcessingJob | None:
        return await self.session.get(MediaProcessingJob, job_id)

    async def get_by_download_job(
        self,
        download_job_id: UUID,
    ) -> MediaProcessingJob | None:
        return await self.session.scalar(
            select(MediaProcessingJob).where(
                MediaProcessingJob.download_job_id == download_job_id,
            ),
        )

    async def get_latest_for_episode(
        self,
        episode_id: UUID,
    ) -> MediaProcessingJob | None:
        return await self.session.scalar(
            select(MediaProcessingJob)
            .where(MediaProcessingJob.episode_id == episode_id)
            .order_by(MediaProcessingJob.created_at.desc()),
        )

    async def add(self, job: MediaProcessingJob) -> MediaProcessingJob:
        self.session.add(job)
        await self.session.flush()
        return job
