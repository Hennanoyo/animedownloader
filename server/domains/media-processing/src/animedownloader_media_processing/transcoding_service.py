from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .enums import MediaTranscodingJobStatus, MediaTranscodingOperation, MediaVariantKind
from .exceptions import MediaTranscodingJobNotFoundError
from .models import MediaTranscodingJob, MediaVariant
from .repository import MediaProcessingJobRepository


class MediaTranscodingJobService:
    def __init__(self, session: AsyncSession) -> None:
        self.jobs = MediaProcessingJobRepository(session)

    async def get_job(self, job_id: UUID) -> MediaTranscodingJob:
        job = await self.jobs.get_transcoding_job(job_id)
        if job is None:
            raise MediaTranscodingJobNotFoundError(job_id)
        return job

    async def get_latest_job(self, media_asset_id: UUID) -> MediaTranscodingJob | None:
        return await self.jobs.get_latest_transcoding_job(media_asset_id)

    async def create_job(
        self,
        *,
        media_asset_id: UUID,
        source_path: str,
        source_metadata_updated_at: datetime,
    ) -> MediaTranscodingJob | None:
        await self.jobs.session.rollback()
        async with self.jobs.session.begin():
            active = await self.jobs.get_active_transcoding_job(media_asset_id)
            if active is not None:
                return None

            variant = await self.jobs.get_playable_variant(media_asset_id)
            if variant is not None and variant.is_current(
                source_path=source_path,
                source_metadata_updated_at=source_metadata_updated_at,
            ):
                return None

            if variant is None:
                variant = MediaVariant(
                    media_asset_id=media_asset_id,
                    kind=MediaVariantKind.PLAYABLE.value,
                )
                await self.jobs.add_variant(variant)

            job = MediaTranscodingJob(
                media_asset_id=media_asset_id,
                variant_id=variant.id,
                source_path=source_path,
                source_metadata_updated_at=source_metadata_updated_at,
            )
            await self.jobs.add_transcoding_job(job)

        await self.jobs.session.refresh(job)
        return job

    async def mark_processing(
        self,
        job_id: UUID,
        operation: MediaTranscodingOperation,
    ) -> MediaTranscodingJob:
        await self.jobs.session.rollback()
        async with self.jobs.session.begin():
            job = await self.get_job(job_id)
            variant = await self.jobs.get_variant(job.variant_id)
            if variant is None:
                raise MediaTranscodingJobNotFoundError(job.variant_id)

            job.operation = operation.value
            job.transition_to(MediaTranscodingJobStatus.PROCESSING)
            variant.mark_processing()

        await self.jobs.session.refresh(job)
        return job

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        output_path: str,
        format_name: str | None,
        duration_seconds: float | None,
        size_bytes: int | None,
        video_codec: str | None,
        audio_codec: str | None,
        width: int | None,
        height: int | None,
        frame_rate: str | None,
    ) -> MediaTranscodingJob:
        await self.jobs.session.rollback()
        async with self.jobs.session.begin():
            job = await self.get_job(job_id)
            variant = await self.jobs.get_variant(job.variant_id)
            if variant is None:
                raise MediaTranscodingJobNotFoundError(job.variant_id)

            job.output_path = output_path
            job.transition_to(MediaTranscodingJobStatus.COMPLETED)
            variant.mark_completed(
                source_path=job.source_path,
                source_metadata_updated_at=job.source_metadata_updated_at,
                output_path=output_path,
                format_name=format_name,
                duration_seconds=duration_seconds,
                size_bytes=size_bytes,
                video_codec=video_codec,
                audio_codec=audio_codec,
                width=width,
                height=height,
                frame_rate=frame_rate,
            )

        await self.jobs.session.refresh(job)
        return job

    async def mark_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
    ) -> MediaTranscodingJob:
        await self.jobs.session.rollback()
        async with self.jobs.session.begin():
            job = await self.get_job(job_id)
            variant = await self.jobs.get_variant(job.variant_id)
            if variant is None:
                raise MediaTranscodingJobNotFoundError(job.variant_id)

            job.transition_to(MediaTranscodingJobStatus.FAILED)
            job.error_message = error_message[:2000]
            variant.mark_failed(error_message)

        await self.jobs.session.refresh(job)
        return job
