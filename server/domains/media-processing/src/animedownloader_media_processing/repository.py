from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import MediaPreparationJobStatus
from .models import MediaPreparationJob, MediaProcessingJob, MediaTranscodingJob, MediaVariant


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

    async def get_variant(self, variant_id: UUID) -> MediaVariant | None:
        return await self.session.get(MediaVariant, variant_id)

    async def get_playable_variant(self, media_asset_id: UUID) -> MediaVariant | None:
        return await self.session.scalar(
            select(MediaVariant).where(
                MediaVariant.media_asset_id == media_asset_id,
                MediaVariant.kind == "playable",
            ),
        )

    async def add_variant(self, variant: MediaVariant) -> MediaVariant:
        self.session.add(variant)
        await self.session.flush()
        return variant

    async def get_preparation_job(self, job_id: UUID) -> MediaPreparationJob | None:
        return await self.session.get(MediaPreparationJob, job_id)

    async def get_latest_preparation_job(
        self,
        media_asset_id: UUID,
    ) -> MediaPreparationJob | None:
        return await self.session.scalar(
            select(MediaPreparationJob)
            .where(MediaPreparationJob.media_asset_id == media_asset_id)
            .order_by(MediaPreparationJob.created_at.desc()),
        )

    async def get_active_preparation_job(
        self,
        media_asset_id: UUID,
    ) -> MediaPreparationJob | None:
        return await self.session.scalar(
            select(MediaPreparationJob)
            .where(
                MediaPreparationJob.media_asset_id == media_asset_id,
                MediaPreparationJob.status.in_(
                    (
                        MediaPreparationJobStatus.PENDING.value,
                        MediaPreparationJobStatus.PROCESSING.value,
                    ),
                ),
            )
            .order_by(MediaPreparationJob.created_at.desc()),
        )

    async def add_preparation_job(
        self,
        job: MediaPreparationJob,
    ) -> MediaPreparationJob:
        self.session.add(job)
        await self.session.flush()
        return job

