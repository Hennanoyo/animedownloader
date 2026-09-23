from datetime import datetime
from uuid import UUID

from animedownloader_media_asset import MediaAssetService
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import (
    MediaPreparationJobStatus,
    MediaTranscodingOperation,
    MediaVariantKind,
)
from .exceptions import MediaPreparationJobNotFoundError
from .models import MediaPreparationJob, MediaVariant
from .repository import MediaProcessingJobRepository


class MediaPreparationJobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.jobs = MediaProcessingJobRepository(session)

    async def get_job(self, job_id: UUID) -> MediaPreparationJob:
        job = await self.jobs.get_preparation_job(job_id)
        if job is None:
            raise MediaPreparationJobNotFoundError(job_id)
        return job

    async def get_latest_job(
        self,
        media_asset_id: UUID,
    ) -> MediaPreparationJob | None:
        return await self.jobs.get_latest_preparation_job(media_asset_id)

    async def create_job(
        self,
        *,
        media_asset_id: UUID,
        source_path: str,
        source_metadata_updated_at: datetime,
        thumbnail_ready: bool,
    ) -> MediaPreparationJob | None:
        await self.session.rollback()
        async with self.session.begin():
            active = await self.jobs.get_active_preparation_job(media_asset_id)
            if active is not None:
                return None

            variant = await self.jobs.get_playable_variant(media_asset_id)
            if variant is not None:
                playable_ready = variant.is_current(
                    source_path=source_path,
                    source_metadata_updated_at=source_metadata_updated_at,
                )
            else:
                playable_ready = False

            if playable_ready and thumbnail_ready:
                return None

            if variant is None:
                variant = MediaVariant(
                    media_asset_id=media_asset_id,
                    kind=MediaVariantKind.PLAYABLE.value,
                )
                await self.jobs.add_variant(variant)

            job = MediaPreparationJob(
                media_asset_id=media_asset_id,
                variant_id=variant.id,
                source_path=source_path,
                source_metadata_updated_at=source_metadata_updated_at,
            )
            await self.jobs.add_preparation_job(job)

        await self.session.refresh(job)
        return job

    async def mark_processing(
        self,
        job_id: UUID,
        *,
        operation: MediaTranscodingOperation | None,
        playable_required: bool,
        thumbnail_required: bool,
    ) -> MediaPreparationJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            variant = await self.jobs.get_variant(job.variant_id)
            if variant is None:
                raise MediaPreparationJobNotFoundError(job.variant_id)
            asset = await MediaAssetService(self.session).get(job.media_asset_id)
            if asset is None:
                raise MediaPreparationJobNotFoundError(job.media_asset_id)

            job.operation = operation.value if operation is not None else None
            job.transition_to(MediaPreparationJobStatus.PROCESSING)
            if playable_required:
                variant.mark_processing()
            if thumbnail_required:
                asset.mark_thumbnail_processing()

        await self.session.refresh(job)
        return job

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        playable_output_path: str | None,
        format_name: str | None,
        duration_seconds: float | None,
        size_bytes: int | None,
        video_codec: str | None,
        audio_codec: str | None,
        width: int | None,
        height: int | None,
        frame_rate: str | None,
        thumbnail_sprite_path: str | None,
        thumbnail_vtt_path: str | None,
    ) -> MediaPreparationJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            variant = await self.jobs.get_variant(job.variant_id)
            if variant is None:
                raise MediaPreparationJobNotFoundError(job.variant_id)
            asset = await MediaAssetService(self.session).get(job.media_asset_id)
            if asset is None:
                raise MediaPreparationJobNotFoundError(job.media_asset_id)

            if playable_output_path is not None:
                variant.mark_completed(
                    source_path=job.source_path,
                    source_metadata_updated_at=job.source_metadata_updated_at,
                    output_path=playable_output_path,
                    format_name=format_name,
                    duration_seconds=duration_seconds,
                    size_bytes=size_bytes,
                    video_codec=video_codec,
                    audio_codec=audio_codec,
                    width=width,
                    height=height,
                    frame_rate=frame_rate,
                )

            if thumbnail_sprite_path is not None and thumbnail_vtt_path is not None:
                asset.mark_thumbnail_completed(
                    sprite_path=thumbnail_sprite_path,
                    vtt_path=thumbnail_vtt_path,
                )

            job.transition_to(MediaPreparationJobStatus.COMPLETED)

        await self.session.refresh(job)
        return job

    async def mark_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
    ) -> MediaPreparationJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            variant = await self.jobs.get_variant(job.variant_id)
            asset = await MediaAssetService(self.session).get(job.media_asset_id)
            if variant is None:
                raise MediaPreparationJobNotFoundError(job.variant_id)
            if asset is None:
                raise MediaPreparationJobNotFoundError(job.media_asset_id)

            if variant.variant_status.value == "processing":
                variant.mark_failed(error_message)
            if asset.thumbnail_processing_status.value == "processing":
                asset.mark_thumbnail_failed(error_message)

            job.transition_to(MediaPreparationJobStatus.FAILED)
            job.error_message = error_message[:2000]

        await self.session.refresh(job)
        return job
