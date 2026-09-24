from contextlib import suppress
from uuid import UUID

from animedownloader_anime import AnimeService
from animedownloader_download import DownloadJobService, DownloadJobStatus
from animedownloader_media_asset import MediaAssetService
from animedownloader_media_processing import (
    MediaPreparationJobService,
    MediaPreparationJobStatus,
    MediaProcessingJobService,
    MediaProcessingJobStatus,
    MediaStreamingPackageService,
    MediaVariantService,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .media_processing_queue import MediaProcessingTaskDispatcher
from .schemas import (
    EpisodePipelineCurrentStage,
    EpisodePipelineRetryResponse,
    EpisodePipelineStageStatus,
)
from .task_queue import DownloadTaskDispatcher


class EpisodePipelineRetryConflictError(RuntimeError):
    pass


class EpisodePipelineQueueError(RuntimeError):
    pass


class EpisodePipelineControlService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        download_dispatcher: DownloadTaskDispatcher,
        media_dispatcher: MediaProcessingTaskDispatcher,
    ) -> None:
        self._anime = AnimeService(session)
        self._downloads = DownloadJobService(session)
        self._processing = MediaProcessingJobService(session)
        self._assets = MediaAssetService(session)
        self._preparation = MediaPreparationJobService(session)
        self._variants = MediaVariantService(session)
        self._streaming = MediaStreamingPackageService(session)
        self._download_dispatcher = download_dispatcher
        self._media_dispatcher = media_dispatcher

    async def retry(self, episode_id: UUID) -> EpisodePipelineRetryResponse:
        await self._anime.get_episode(episode_id)

        download = await self._downloads.get_latest_job(episode_id)
        if download is None or download.job_status in {
            DownloadJobStatus.FAILED,
            DownloadJobStatus.CANCELLED,
        }:
            job = await self._downloads.create_job(episode_id)
            await self._enqueue_download(job.id)
            return EpisodePipelineRetryResponse(
                stage=EpisodePipelineCurrentStage.DOWNLOAD,
                job_id=job.id,
                status=EpisodePipelineStageStatus.PENDING,
            )

        if download.job_status in {
            DownloadJobStatus.PENDING,
            DownloadJobStatus.DOWNLOADING,
            DownloadJobStatus.PAUSED,
        }:
            raise EpisodePipelineRetryConflictError(
                "Download is already active. Resume or cancel the download first.",
            )

        processing = await self._processing.get_latest_job(episode_id)
        if processing is None:
            job = await self._processing.create_job(episode_id, download.id)
            await self._enqueue_processing(job.id)
            return EpisodePipelineRetryResponse(
                stage=EpisodePipelineCurrentStage.PROCESSING,
                job_id=job.id,
                status=EpisodePipelineStageStatus.PENDING,
            )

        processing_status = processing.job_status
        if processing_status is MediaProcessingJobStatus.FAILED:
            job = await self._processing.retry_job(processing.id)
            await self._enqueue_processing(job.id)
            return EpisodePipelineRetryResponse(
                stage=EpisodePipelineCurrentStage.PROCESSING,
                job_id=job.id,
                status=EpisodePipelineStageStatus.PENDING,
            )
        if processing_status is MediaProcessingJobStatus.PENDING:
            await self._enqueue_processing(processing.id)
            return EpisodePipelineRetryResponse(
                stage=EpisodePipelineCurrentStage.PROCESSING,
                job_id=processing.id,
                status=EpisodePipelineStageStatus.PENDING,
            )
        if processing_status is MediaProcessingJobStatus.PROCESSING:
            raise EpisodePipelineRetryConflictError(
                "Media processing is already in progress.",
            )

        asset = await self._assets.get_for_episode(episode_id)
        if asset is None or not asset.metadata_ready:
            await self._enqueue_processing(processing.id)
            return EpisodePipelineRetryResponse(
                stage=EpisodePipelineCurrentStage.PROCESSING,
                job_id=processing.id,
                status=EpisodePipelineStageStatus.PENDING,
            )

        if asset.metadata_updated_at is None:
            await self._enqueue_processing(processing.id)
            return EpisodePipelineRetryResponse(
                stage=EpisodePipelineCurrentStage.PROCESSING,
                job_id=processing.id,
                status=EpisodePipelineStageStatus.PENDING,
            )

        variant = await self._variants.get_playable_variant(asset.id)
        playable_ready = (
            variant is not None
            and variant.is_current(
                source_path=asset.path,
                source_metadata_updated_at=asset.metadata_updated_at,
            )
        )
        thumbnail_ready = asset.thumbnail_ready

        if not playable_ready or not thumbnail_ready:
            stage = (
                EpisodePipelineCurrentStage.PROCESSING
                if not playable_ready
                else EpisodePipelineCurrentStage.PREVIEW
            )
            preparation = await self._preparation.get_latest_job(asset.id)
            if preparation is not None:
                preparation_status = preparation.job_status
                if preparation_status is MediaPreparationJobStatus.PROCESSING:
                    raise EpisodePipelineRetryConflictError(
                        "Media preparation is already in progress.",
                    )
                if preparation_status is MediaPreparationJobStatus.PENDING:
                    await self._enqueue_preparation(preparation.id)
                    return EpisodePipelineRetryResponse(
                        stage=stage,
                        job_id=preparation.id,
                        status=EpisodePipelineStageStatus.PENDING,
                    )

            preparation = await self._preparation.create_job(
                media_asset_id=asset.id,
                source_path=asset.path,
                source_metadata_updated_at=asset.metadata_updated_at,
                thumbnail_ready=thumbnail_ready,
            )
            if preparation is None:
                raise EpisodePipelineRetryConflictError(
                    "Media preparation is already active or complete.",
                )
            await self._enqueue_preparation(preparation.id)
            return EpisodePipelineRetryResponse(
                stage=stage,
                job_id=preparation.id,
                status=EpisodePipelineStageStatus.PENDING,
            )

        if variant is None or variant.path is None:
            raise EpisodePipelineRetryConflictError(
                "Playable media is not ready for streaming packaging.",
            )

        active_package = await self._streaming.get_active_job(variant.id)
        if active_package is not None:
            raise EpisodePipelineRetryConflictError(
                "Media streaming packaging is already in progress.",
            )

        package = await self._streaming.get_for_variant(variant.id)
        if package is not None and package.is_current(
            source_path=variant.path,
            source_variant_updated_at=variant.updated_at,
        ):
            raise EpisodePipelineRetryConflictError(
                "Media streaming package is already complete.",
            )

        job = await self._streaming.create_job(media_variant_id=variant.id)
        if job is None:
            raise EpisodePipelineRetryConflictError(
                "Media streaming packaging is already active or complete.",
            )
        await self._enqueue_packaging(job.id)
        return EpisodePipelineRetryResponse(
            stage=EpisodePipelineCurrentStage.STREAMING,
            job_id=job.id,
            status=EpisodePipelineStageStatus.PENDING,
        )

    async def _enqueue_download(self, job_id: UUID) -> None:
        try:
            await self._download_dispatcher.enqueue(job_id)
        except Exception as exc:
            with suppress(Exception):
                await self._downloads.mark_failed(
                    job_id,
                    error_message="Failed to enqueue download task.",
                )
            raise EpisodePipelineQueueError(
                "Download task queue is temporarily unavailable",
            ) from exc

    async def _enqueue_processing(self, job_id: UUID) -> None:
        try:
            await self._media_dispatcher.enqueue(job_id)
        except Exception as exc:
            with suppress(Exception):
                await self._processing.mark_failed(
                    job_id,
                    error_message="Failed to enqueue media processing task.",
                )
            raise EpisodePipelineQueueError(
                "Media processing task queue is temporarily unavailable",
            ) from exc

    async def _enqueue_preparation(self, job_id: UUID) -> None:
        try:
            await self._media_dispatcher.enqueue_preparation(job_id)
        except Exception as exc:
            with suppress(Exception):
                await self._preparation.mark_failed(
                    job_id,
                    error_message="Failed to enqueue media preparation task.",
                )
            raise EpisodePipelineQueueError(
                "Media preparation task queue is temporarily unavailable",
            ) from exc

    async def _enqueue_packaging(self, job_id: UUID) -> None:
        try:
            await self._media_dispatcher.enqueue_packaging(job_id)
        except Exception as exc:
            with suppress(Exception):
                await self._streaming.mark_failed(
                    job_id,
                    error_message="Failed to enqueue media packaging task.",
                )
            raise EpisodePipelineQueueError(
                "Media packaging task queue is temporarily unavailable",
            ) from exc
