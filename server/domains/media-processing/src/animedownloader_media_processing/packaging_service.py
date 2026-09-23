from uuid import UUID

from animedownloader_media_asset import MediaAssetService
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import (
    MediaPackagingJobStatus,
    MediaStreamingPackageStatus,
    MediaStreamingRepresentationStatus,
)
from .exceptions import (
    MediaPackagingJobNotFoundError,
    MediaStreamingPackageNotFoundError,
    MediaStreamingVariantNotFoundError,
)
from .models import MediaVariant
from .packaging_models import (
    MediaPackagingJob,
    MediaStreamingPackage,
    MediaStreamingRepresentation,
)
from .packaging_repo import MediaPackagingRepository


class MediaStreamingPackageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.packages = MediaPackagingRepository(session)

    async def get_variant(self, variant_id: UUID) -> MediaVariant | None:
        return await self.packages.get_variant(variant_id)

    async def get_package(self, package_id: UUID) -> MediaStreamingPackage:
        package = await self.packages.get_package(package_id)
        if package is None:
            raise MediaStreamingPackageNotFoundError(package_id)
        return package

    async def get_for_variant(
        self,
        variant_id: UUID,
    ) -> MediaStreamingPackage | None:
        return await self.packages.get_package_by_variant(variant_id)

    async def get_job(self, job_id: UUID) -> MediaPackagingJob:
        job = await self.packages.get_job(job_id)
        if job is None:
            raise MediaPackagingJobNotFoundError(job_id)
        return job

    async def get_latest_job(self, variant_id: UUID) -> MediaPackagingJob | None:
        return await self.packages.get_latest_job(variant_id)

    async def create_job(
        self,
        *,
        media_variant_id: UUID,
    ) -> MediaPackagingJob | None:
        await self.session.rollback()
        async with self.session.begin():
            variant = await self.packages.get_variant(media_variant_id)
            if variant is None:
                raise MediaStreamingVariantNotFoundError(media_variant_id)

            variant_path = variant.path
            if not variant.ready or variant_path is None:
                raise MediaStreamingVariantNotFoundError(media_variant_id)

            asset = await MediaAssetService(self.session).get(variant.media_asset_id)
            if asset is None or asset.metadata_updated_at is None:
                raise MediaStreamingVariantNotFoundError(media_variant_id)

            if not variant.is_current(
                source_path=asset.path,
                source_metadata_updated_at=asset.metadata_updated_at,
            ):
                raise MediaStreamingVariantNotFoundError(media_variant_id)

            active = await self.packages.get_active_job(media_variant_id)
            if active is not None:
                return None

            package = await self.packages.get_package_by_variant(media_variant_id)
            if package is not None and package.is_current(
                source_path=variant_path,
                source_variant_updated_at=variant.updated_at,
            ):
                return None

            if package is None:
                package = await self.packages.add_package(
                    MediaStreamingPackage(
                        media_variant_id=media_variant_id,
                        status=MediaStreamingPackageStatus.PENDING.value,
                        source_path=variant_path,
                        source_variant_updated_at=variant.updated_at,
                    ),
                )
            else:
                package.status = MediaStreamingPackageStatus.PENDING.value
                package.source_path = variant_path
                package.source_variant_updated_at = variant.updated_at
                package.hls_master_key = None
                package.dash_manifest_key = None
                package.error_message = None
                await self.packages.delete_representations(package.id)

            job = await self.packages.add_job(
                MediaPackagingJob(
                    media_variant_id=media_variant_id,
                    package_id=package.id,
                    source_path=variant_path,
                    source_variant_updated_at=variant.updated_at,
                ),
            )

        await self.session.refresh(job)
        return job

    async def mark_processing(self, job_id: UUID) -> MediaPackagingJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            package = await self.packages.get_package(job.package_id)
            if package is None:
                raise MediaStreamingPackageNotFoundError(job.package_id)

            job.transition_to(MediaPackagingJobStatus.PROCESSING)
            package.status = MediaStreamingPackageStatus.PROCESSING.value
            package.error_message = None

        await self.session.refresh(job)
        return job

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        hls_master_key: str,
        dash_manifest_key: str,
        quality: str,
        width: int,
        height: int,
        bandwidth: int,
        video_codec: str,
        audio_codec: str | None,
        duration_seconds: float,
        hls_playlist_key: str,
        init_segment_key: str,
        segment_directory_key: str,
    ) -> MediaPackagingJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            package = await self.packages.get_package(job.package_id)
            if package is None:
                raise MediaStreamingPackageNotFoundError(job.package_id)

            self.session.add(
                MediaStreamingRepresentation(
                    package_id=package.id,
                    quality=quality,
                    width=width,
                    height=height,
                    bandwidth=bandwidth,
                    video_codec=video_codec,
                    audio_codec=audio_codec,
                    duration_seconds=duration_seconds,
                    hls_playlist_key=hls_playlist_key,
                    init_segment_key=init_segment_key,
                    segment_directory_key=segment_directory_key,
                    status=MediaStreamingRepresentationStatus.COMPLETED.value,
                ),
            )
            package.hls_master_key = hls_master_key
            package.dash_manifest_key = dash_manifest_key
            package.source_path = job.source_path
            package.source_variant_updated_at = job.source_variant_updated_at
            package.status = MediaStreamingPackageStatus.COMPLETED.value
            package.error_message = None
            job.transition_to(MediaPackagingJobStatus.COMPLETED)

        await self.session.refresh(job)
        return job

    async def mark_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
    ) -> MediaPackagingJob:
        await self.session.rollback()
        async with self.session.begin():
            job = await self.get_job(job_id)
            package = await self.packages.get_package(job.package_id)
            if package is None:
                raise MediaStreamingPackageNotFoundError(job.package_id)

            if job.job_status is not MediaPackagingJobStatus.FAILED:
                job.transition_to(MediaPackagingJobStatus.FAILED)

            package.status = MediaStreamingPackageStatus.FAILED.value
            package.error_message = error_message[:2000]

        await self.session.refresh(job)
        return job
