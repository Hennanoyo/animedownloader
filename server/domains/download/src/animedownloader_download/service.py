from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .enums import DownloadJobStatus
from .exceptions import DownloadJobNotFoundError
from .models import DownloadJob
from .repository import DownloadJobRepository


class DownloadJobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.jobs = DownloadJobRepository(session)

    async def get_job(self, job_id: UUID) -> DownloadJob:
        job = await self.jobs.get(job_id)
        if job is None:
            raise DownloadJobNotFoundError(job_id)
        return job

    async def get_active_job(self, episode_id: UUID) -> DownloadJob | None:
        return await self.jobs.get_active_for_episode(episode_id)

    async def mark_downloading(self, job_id: UUID) -> DownloadJob:
        return await self._transition(job_id, DownloadJobStatus.DOWNLOADING)

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        downloaded_bytes: int | None = None,
        total_bytes: int | None = None,
    ) -> DownloadJob:
        return await self._transition(
            job_id,
            DownloadJobStatus.COMPLETED,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
        )

    async def mark_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
    ) -> DownloadJob:
        return await self._transition(
            job_id,
            DownloadJobStatus.FAILED,
            error_message=error_message,
        )

    async def mark_cancelled(self, job_id: UUID) -> DownloadJob:
        return await self._transition(job_id, DownloadJobStatus.CANCELLED)

    async def _transition(
        self,
        job_id: UUID,
        status: DownloadJobStatus,
        *,
        error_message: str | None = None,
        downloaded_bytes: int | None = None,
        total_bytes: int | None = None,
    ) -> DownloadJob:
        async with self.session.begin():
            job = await self.get_job(job_id)
            job.transition_to(
                status,
                error_message=error_message,
                downloaded_bytes=downloaded_bytes,
                total_bytes=total_bytes,
            )

        await self.session.refresh(job)
        return job
