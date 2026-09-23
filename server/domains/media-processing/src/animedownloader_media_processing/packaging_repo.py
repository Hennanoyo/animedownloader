from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .enums import MediaPackagingJobStatus
from .models import MediaVariant
from .packaging_models import (
    MediaPackagingJob,
    MediaStreamingPackage,
    MediaStreamingRepresentation,
)


class MediaPackagingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_variant(self, variant_id: UUID) -> MediaVariant | None:
        return await self.session.get(MediaVariant, variant_id)

    async def get_package(self, package_id: UUID) -> MediaStreamingPackage | None:
        return await self.session.scalar(
            select(MediaStreamingPackage)
            .options(selectinload(MediaStreamingPackage.representations))
            .where(MediaStreamingPackage.id == package_id),
        )

    async def get_package_by_variant(
        self,
        variant_id: UUID,
    ) -> MediaStreamingPackage | None:
        return await self.session.scalar(
            select(MediaStreamingPackage)
            .options(selectinload(MediaStreamingPackage.representations))
            .where(MediaStreamingPackage.media_variant_id == variant_id),
        )

    async def get_job(self, job_id: UUID) -> MediaPackagingJob | None:
        return await self.session.get(MediaPackagingJob, job_id)

    async def get_latest_job(
        self,
        variant_id: UUID,
    ) -> MediaPackagingJob | None:
        return await self.session.scalar(
            select(MediaPackagingJob)
            .where(MediaPackagingJob.media_variant_id == variant_id)
            .order_by(MediaPackagingJob.created_at.desc()),
        )

    async def get_active_job(
        self,
        variant_id: UUID,
    ) -> MediaPackagingJob | None:
        return await self.session.scalar(
            select(MediaPackagingJob)
            .where(
                MediaPackagingJob.media_variant_id == variant_id,
                MediaPackagingJob.status.in_(
                    (
                        MediaPackagingJobStatus.PENDING.value,
                        MediaPackagingJobStatus.PROCESSING.value,
                    ),
                ),
            )
            .order_by(MediaPackagingJob.created_at.desc()),
        )

    async def add_package(
        self,
        package: MediaStreamingPackage,
    ) -> MediaStreamingPackage:
        self.session.add(package)
        await self.session.flush()
        return package

    async def add_job(self, job: MediaPackagingJob) -> MediaPackagingJob:
        self.session.add(job)
        await self.session.flush()
        return job

    async def delete_representations(self, package_id: UUID) -> None:
        await self.session.execute(
            delete(MediaStreamingRepresentation).where(
                MediaStreamingRepresentation.package_id == package_id,
            ),
        )
