from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import DownloadJobStatus
from .models import DownloadJob


class DownloadJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, job_id: UUID) -> DownloadJob | None:
        return await self.session.get(DownloadJob, job_id)

    async def get_active_for_episode(self, episode_id: UUID) -> DownloadJob | None:
        result = await self.session.scalar(
            select(DownloadJob)
            .where(
                DownloadJob.episode_id == episode_id,
                DownloadJob.status.in_(
                    (
                        DownloadJobStatus.PENDING.value,
                        DownloadJobStatus.DOWNLOADING.value,
                    )
                ),
            )
            .order_by(DownloadJob.created_at.desc())
        )
        return result

    async def get_latest_for_episode(self, episode_id: UUID) -> DownloadJob | None:
        result = await self.session.scalar(
            select(DownloadJob)
            .where(DownloadJob.episode_id == episode_id)
            .order_by(DownloadJob.created_at.desc())
        )
        return result

    async def add(self, job: DownloadJob) -> DownloadJob:
        self.session.add(job)
        await self.session.flush()
        return job
