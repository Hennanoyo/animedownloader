from uuid import UUID

from animedownloader_anime import Anime, Episode
from sqlalchemy import func, select
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
                        DownloadJobStatus.PAUSED.value,
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

    async def list_with_context(
        self,
        *,
        statuses: tuple[DownloadJobStatus, ...] | None,
        offset: int,
        limit: int,
    ) -> tuple[list[tuple[DownloadJob, Episode, Anime]], int]:
        filters = (
            [DownloadJob.status.in_(tuple(status.value for status in statuses))]
            if statuses
            else []
        )

        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(DownloadJob)
                .where(*filters)
            )
            or 0
        )

        result = await self.session.execute(
            select(DownloadJob, Episode, Anime)
            .join(Episode, DownloadJob.episode_id == Episode.id)
            .join(Anime, Episode.anime_id == Anime.id)
            .where(*filters)
            .order_by(DownloadJob.created_at.desc(), DownloadJob.id.desc())
            .offset(offset)
            .limit(limit)
        )

        return list(result.tuples().all()), total

    async def add(self, job: DownloadJob) -> DownloadJob:
        self.session.add(job)
        await self.session.flush()
        return job

    async def delete(self, job: DownloadJob) -> None:
        await self.session.delete(job)
