from datetime import datetime
from uuid import UUID

from animedownloader_anime import Episode, EpisodeNotFoundError
from animedownloader_download import (
    DownloadJob,
    DownloadJobNotFoundError,
    DownloadJobStatus,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import (
    MediaProcessingJobStatus,
    MediaTranscodingJobStatus,
    MediaVariantKind,
)
from .exceptions import (
    MediaProcessingJobNotFoundError,
    MediaTranscodingJobNotFoundError,
)
from .models import MediaProcessingJob, MediaTranscodingJob, MediaVariant
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

    async def create_for_download_job(
        self,
        download_job_id: UUID,
    ) -> MediaProcessingJob:
        await self.session.rollback()
        async with self.session.begin():
            download_job = await self.session.get(DownloadJob, download_job_id)
            if download_job is None:
                raise DownloadJobNotFoundError(download_job_id)

            if download_job.job_status is not DownloadJobStatus.COMPLETED:
                raise ValueError(
                    "Media processing requires a completed download job",
                )

            existing = await self.jobs.get_by_download_job(download_job_id)
            if existing is not None:
                return existing

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
        return job

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

    async def get_playable_variant(self, media_asset_id: UUID) -> MediaVariant | None:
        return await self.jobs.get_playable_variant(media_asset_id)

    async def get_transcoding_job(self, job_id: UUID) -> MediaTranscodingJob:
        job = await self.jobs.get_transcoding_job(job_id)
        if job is None:
            raise MediaTranscodingJobNotFoundError(job_id)
        return job

    async def get_latest_transcoding_job(
        self,
        media_asset_id: UUID,
    ) -> MediaTranscodingJob | None:
        return await self.jobs.get_latest_transcoding_job(media_asset_id)

    async def create_transcoding_job(
        self,
        *,
        media_asset_id: UUID,
        source_path: str,
        source_metadata_updated_at: datetime,
    ) -> MediaTranscodingJob | None:
        await self.session.rollback()
        async with self.session.begin():
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

        await self.session.refresh(job)
        return job

    async def mark_transcoding_processing(
        self,
        job_id: UUID,
        operation,
    ) -> MediaTranscodingJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_transcoding_job(job_id)
            variant = await self.jobs.get_variant(job.variant_id)
            if variant is None:
                raise MediaTranscodingJobNotFoundError(job.variant_id)
            job.operation = operation.value
            job.transition_to(MediaTranscodingJobStatus.PROCESSING)
            variant.mark_processing()

        await self.session.refresh(job)
        return job

    async def mark_transcoding_completed(
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
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_transcoding_job(job_id)
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

        await self.session.refresh(job)
        return job

    async def mark_transcoding_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
    ) -> MediaTranscodingJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_transcoding_job(job_id)
            variant = await self.jobs.get_variant(job.variant_id)
            if variant is None:
                raise MediaTranscodingJobNotFoundError(job.variant_id)
            job.transition_to(MediaTranscodingJobStatus.FAILED)
            job.error_message = error_message[:2000]
            variant.mark_failed(error_message)

        await self.session.refresh(job)
        return job
