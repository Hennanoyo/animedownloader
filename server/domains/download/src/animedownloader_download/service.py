from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from animedownloader_anime import Anime, Episode, EpisodeNotFoundError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import DownloadJobStatus
from .exceptions import (
    ActiveDownloadJobError,
    DownloadJobActiveError,
    DownloadJobNotFoundError,
)
from .models import DownloadJob
from .repository import DownloadJobRepository


@dataclass(frozen=True, slots=True)
class DownloadJobListItem:
    job: DownloadJob
    episode: Episode
    anime: Anime


@dataclass(frozen=True, slots=True)
class DownloadJobListResult:
    items: list[DownloadJobListItem]
    total: int


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

    async def get_latest_job(self, episode_id: UUID) -> DownloadJob | None:
        return await self.jobs.get_latest_for_episode(episode_id)

    async def get_latest_completed_job(self, episode_id: UUID) -> DownloadJob | None:
        return await self.jobs.get_latest_completed_for_episode(episode_id)

    async def list_jobs(
        self,
        *,
        statuses: tuple[DownloadJobStatus, ...] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> DownloadJobListResult:
        if page < 1:
            raise ValueError("page must be at least 1")
        if page_size < 1:
            raise ValueError("page_size must be at least 1")

        rows, total = await self.jobs.list_with_context(
            statuses=statuses,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return DownloadJobListResult(
            items=[
                DownloadJobListItem(job=job, episode=episode, anime=anime)
                for job, episode, anime in rows
            ],
            total=total,
        )

    async def create_job(self, episode_id: UUID) -> DownloadJob:
        await self.session.rollback()
        try:
            async with self.session.begin():
                episode = await self.session.get(Episode, episode_id)
                if episode is None:
                    raise EpisodeNotFoundError(episode_id)

                active = await self.jobs.get_active_for_episode(episode_id)
                if active is not None:
                    raise ActiveDownloadJobError(episode_id, active.id)

                job = DownloadJob(episode_id=episode_id)
                await self.jobs.add(job)
        except IntegrityError:
            await self.session.rollback()
            active = await self.jobs.get_active_for_episode(episode_id)
            if active is not None:
                raise ActiveDownloadJobError(episode_id, active.id) from None
            raise

        await self.session.refresh(job)
        return job

    async def update_progress(
        self,
        job_id: UUID,
        *,
        downloaded_bytes: int,
        total_bytes: int,
    ) -> DownloadJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            if job.job_status is DownloadJobStatus.DOWNLOADING:
                job.downloaded_bytes = downloaded_bytes
                job.total_bytes = total_bytes

        await self.session.refresh(job)
        return job

    async def mark_downloading(self, job_id: UUID) -> DownloadJob:
        return await self._transition(job_id, DownloadJobStatus.DOWNLOADING)

    async def mark_paused(self, job_id: UUID) -> DownloadJob:
        return await self._transition(job_id, DownloadJobStatus.PAUSED)

    async def delete_job(self, job_id: UUID) -> None:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            if job.job_status in {
                DownloadJobStatus.PENDING,
                DownloadJobStatus.DOWNLOADING,
                DownloadJobStatus.PAUSED,
            }:
                raise DownloadJobActiveError(job_id)
            await self.jobs.delete(job)

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
        await self.session.rollback()
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
