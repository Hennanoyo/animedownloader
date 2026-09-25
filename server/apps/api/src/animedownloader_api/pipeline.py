from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from animedownloader_anime import AnimeService, Episode
from animedownloader_download import DownloadJob
from animedownloader_media_asset import (
    MediaAsset,
    MediaAttachmentStatus,
    SubtitleTrackStatus,
)
from animedownloader_media_processing import (
    MediaPreparationJob,
    MediaPreparationJobStatus,
    MediaProcessingJob,
    MediaProcessingJobStatus,
    MediaStreamingPackage,
    MediaStreamingPackageStatus,
    MediaVariant,
)
from animedownloader_storage import Storage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .schemas import (
    AnimePipelineResponse,
    EpisodePipelineCurrentStage,
    EpisodePipelineDownloadResponse,
    EpisodePipelineProcessingResponse,
    EpisodePipelineStageStatus,
    EpisodePipelineStreamingResponse,
    EpisodePipelineSummary,
    EpisodePipelineThumbnailResponse,
)

_ACTIVE_STATUSES = {
    EpisodePipelineStageStatus.PENDING,
    EpisodePipelineStageStatus.PROCESSING,
    EpisodePipelineStageStatus.DOWNLOADING,
}


class AnimePipelineService:
    def __init__(self, session: AsyncSession, storage: Storage) -> None:
        self._session = session
        self._storage = storage
        self._anime_service = AnimeService(session)

    async def get_for_anime(self, anime_id: UUID) -> AnimePipelineResponse:
        anime = await self._anime_service.get_anime(anime_id)
        episodes = anime.episodes

        if not episodes:
            return AnimePipelineResponse(anime_id=anime.id, episodes=[])

        episode_ids = [episode.id for episode in episodes]

        download_jobs = await self._load_download_jobs(episode_ids)
        processing_jobs = await self._load_processing_jobs(episode_ids)
        assets = await self._load_assets(episode_ids)

        asset_ids = [asset.id for asset in assets.values()]
        preparation_jobs = await self._load_preparation_jobs(asset_ids)
        variants = await self._load_variants(asset_ids)

        variant_ids = [variant.id for variant in variants.values()]
        packages = await self._load_packages(variant_ids)

        summaries = [
            build_episode_pipeline_summary(
                episode,
                download_job=download_jobs.get(episode.id),
                processing_job=processing_jobs.get(episode.id),
                asset=assets.get(episode.id),
                preparation_job=(
                    preparation_jobs.get(assets[episode.id].id)
                    if episode.id in assets
                    else None
                ),
                variant=(
                    variants.get(assets[episode.id].id)
                    if episode.id in assets
                    else None
                ),
                package=(
                    packages.get(variants[assets[episode.id].id].id)
                    if episode.id in assets and assets[episode.id].id in variants
                    else None
                ),
                storage=self._storage,
            )
            for episode in episodes
        ]
        return AnimePipelineResponse(
            anime_id=anime.id,
            episodes=summaries,
        )

    async def _load_download_jobs(
        self,
        episode_ids: list[UUID],
    ) -> dict[UUID, DownloadJob]:
        result = await self._session.scalars(
            select(DownloadJob)
            .where(DownloadJob.episode_id.in_(episode_ids))
            .order_by(DownloadJob.created_at.desc()),
        )
        return _latest_download_jobs(result.all())

    async def _load_processing_jobs(
        self,
        episode_ids: list[UUID],
    ) -> dict[UUID, MediaProcessingJob]:
        result = await self._session.scalars(
            select(MediaProcessingJob)
            .where(MediaProcessingJob.episode_id.in_(episode_ids))
            .order_by(MediaProcessingJob.created_at.desc()),
        )
        return _latest_processing_jobs(result.all())

    async def _load_assets(
        self,
        episode_ids: list[UUID],
    ) -> dict[UUID, MediaAsset]:
        result = await self._session.scalars(
            select(MediaAsset)
            .options(
                selectinload(MediaAsset.subtitle_tracks),
                selectinload(MediaAsset.attachments),
            )
            .where(MediaAsset.episode_id.in_(episode_ids)),
        )
        return {asset.episode_id: asset for asset in result.all()}

    async def _load_preparation_jobs(
        self,
        asset_ids: list[UUID],
    ) -> dict[UUID, MediaPreparationJob]:
        if not asset_ids:
            return {}
        result = await self._session.scalars(
            select(MediaPreparationJob)
            .where(MediaPreparationJob.media_asset_id.in_(asset_ids))
            .order_by(MediaPreparationJob.created_at.desc()),
        )
        return _latest_preparation_jobs(result.all())

    async def _load_variants(
        self,
        asset_ids: list[UUID],
    ) -> dict[UUID, MediaVariant]:
        if not asset_ids:
            return {}
        result = await self._session.scalars(
            select(MediaVariant)
            .where(
                MediaVariant.media_asset_id.in_(asset_ids),
                MediaVariant.kind == "playable",
            ),
        )
        return {variant.media_asset_id: variant for variant in result.all()}

    async def _load_packages(
        self,
        variant_ids: list[UUID],
    ) -> dict[UUID, MediaStreamingPackage]:
        if not variant_ids:
            return {}
        result = await self._session.scalars(
            select(MediaStreamingPackage).where(
                MediaStreamingPackage.media_variant_id.in_(variant_ids),
            ),
        )
        return {package.media_variant_id: package for package in result.all()}


def build_episode_pipeline_summary(
    episode: Episode,
    *,
    download_job: DownloadJob | None,
    processing_job: MediaProcessingJob | None,
    asset: MediaAsset | None,
    preparation_job: MediaPreparationJob | None,
    variant: MediaVariant | None,
    package: MediaStreamingPackage | None,
    storage: Storage,
) -> EpisodePipelineSummary:
    download_status = _download_status(download_job)
    processing_status, processing_progress = _processing_state(
        processing_job,
        download_status=download_status,
        asset=asset,
        preparation_job=preparation_job,
        variant=variant,
    )
    subtitles_status = _asset_stage_status(
        asset,
        updated_at="subtitle_tracks_updated_at",
        processed_at="subtitle_tracks_processed_at",
        failed_values=(
            track.status == SubtitleTrackStatus.FAILED.value
            for track in asset.subtitle_tracks
        )
        if asset is not None
        else (),
    )
    attachments_status = _asset_stage_status(
        asset,
        updated_at="attachments_updated_at",
        processed_at="attachments_processed_at",
        failed_values=(
            attachment.status == MediaAttachmentStatus.FAILED.value
            for attachment in asset.attachments
        )
        if asset is not None
        else (),
    )

    playback_ready = _is_playback_ready(asset, variant)
    streaming_status, hls_ready, dash_ready, streaming_error = _streaming_status(
        asset,
        variant,
        package,
    )

    thumbnail_status = (
        EpisodePipelineStageStatus.NOT_STARTED
        if asset is None
        else EpisodePipelineStageStatus(asset.thumbnail_status)
    )
    thumbnail_progress = 100 if asset is not None and asset.thumbnail_ready else 0
    thumbnail_url = _thumbnail_public_url(
        storage,
        asset.thumbnail_sprite_path if asset is not None and asset.thumbnail_ready else None,
    )
    thumbnail_vtt_url = _thumbnail_public_url(
        storage,
        asset.thumbnail_vtt_path if asset is not None and asset.thumbnail_ready else None,
    )

    processing_error = _processing_error(
        processing_job,
        preparation_job,
        variant,
    )
    processing = EpisodePipelineProcessingResponse(
        status=processing_status,
        progress_percent=processing_progress,
        error_message=processing_error,
        playable_ready=playback_ready,
    )
    streaming = EpisodePipelineStreamingResponse(
        status=streaming_status,
        hls_ready=hls_ready,
        dash_ready=dash_ready,
        error_message=streaming_error,
    )

    current_stage = _current_stage(
        download_status=download_status,
        processing_status=processing_status,
        thumbnail_status=thumbnail_status,
        streaming_status=streaming_status,
    )

    active = any(
        status in _ACTIVE_STATUSES
        for status in (
            download_status,
            processing.status,
            subtitles_status,
            attachments_status,
            streaming.status,
            thumbnail_status,
        )
    )

    return EpisodePipelineSummary(
        episode_id=episode.id,
        episode_number=episode.episode_number,
        title=episode.title,
        download=EpisodePipelineDownloadResponse(
            job_id=download_job.id if download_job else None,
            status=download_status,
            downloaded_bytes=download_job.downloaded_bytes if download_job else 0,
            total_bytes=download_job.total_bytes if download_job else None,
            error_message=download_job.error_message if download_job else None,
            updated_at=download_job.updated_at if download_job else None,
        ),
        processing=processing,
        subtitles=EpisodePipelineStageStatus(subtitles_status),
        attachments=EpisodePipelineStageStatus(attachments_status),
        streaming=streaming,
        thumbnail=EpisodePipelineThumbnailResponse(
            status=thumbnail_status,
            progress_percent=thumbnail_progress,
            url=thumbnail_url,
            vtt_url=thumbnail_vtt_url,
            error_message=asset.thumbnail_error_message if asset is not None else None,
        ),
        current_stage=current_stage,
        playback_ready=playback_ready,
        active=active,
    )


def _download_status(job: DownloadJob | None) -> EpisodePipelineStageStatus:
    if job is None:
        return EpisodePipelineStageStatus.NOT_STARTED
    return EpisodePipelineStageStatus(job.status)


def _processing_state(
    processing_job: MediaProcessingJob | None,
    *,
    download_status: EpisodePipelineStageStatus,
    asset: MediaAsset | None,
    preparation_job: MediaPreparationJob | None,
    variant: MediaVariant | None,
) -> tuple[EpisodePipelineStageStatus, int]:
    if processing_job is None:
        if download_status is EpisodePipelineStageStatus.COMPLETED:
            return EpisodePipelineStageStatus.PENDING, 0
        return (
            (
                EpisodePipelineStageStatus.PENDING
                if asset is not None
                else EpisodePipelineStageStatus.NOT_STARTED
            ),
            0,
        )

    status = MediaProcessingJobStatus(processing_job.status)
    if status is MediaProcessingJobStatus.FAILED:
        return EpisodePipelineStageStatus.FAILED, 0
    if status is MediaProcessingJobStatus.PENDING:
        return EpisodePipelineStageStatus.PENDING, 0
    if status is MediaProcessingJobStatus.PROCESSING:
        return EpisodePipelineStageStatus.PROCESSING, 0

    if preparation_job is None:
        return EpisodePipelineStageStatus.PENDING, 0

    preparation_status = MediaPreparationJobStatus(preparation_job.status)
    playable_ready = _is_playback_ready(asset, variant)
    if preparation_status is MediaPreparationJobStatus.FAILED:
        return (
            EpisodePipelineStageStatus.FAILED,
            100 if playable_ready else 0,
        )
    if playable_ready:
        return EpisodePipelineStageStatus.COMPLETED, 100
    if preparation_status is MediaPreparationJobStatus.PROCESSING:
        return EpisodePipelineStageStatus.PROCESSING, 0
    if preparation_status is MediaPreparationJobStatus.PENDING:
        return EpisodePipelineStageStatus.PENDING, 0
    return EpisodePipelineStageStatus.PENDING, 0


def _asset_stage_status(
    asset: MediaAsset | None,
    *,
    updated_at: str,
    processed_at: str,
    failed_values: Iterable[bool],
) -> EpisodePipelineStageStatus:
    if asset is None or getattr(asset, updated_at) is None:
        return EpisodePipelineStageStatus.NOT_STARTED
    if any(failed_values):
        return EpisodePipelineStageStatus.FAILED
    if getattr(asset, processed_at) is not None:
        return EpisodePipelineStageStatus.COMPLETED
    return EpisodePipelineStageStatus.PROCESSING


def _thumbnail_public_url(storage: Storage, object_key: str | None) -> str | None:
    if object_key is None:
        return None
    return storage.public_url(object_key)


def _is_playback_ready(
    asset: MediaAsset | None,
    variant: MediaVariant | None,
) -> bool:
    if asset is None or variant is None or not variant.ready or variant.path is None:
        return False
    if asset.metadata_updated_at is None:
        return False
    return variant.is_current(
        source_path=asset.path,
        source_metadata_updated_at=asset.metadata_updated_at,
    )


def _processing_error(
    processing_job: MediaProcessingJob | None,
    preparation_job: MediaPreparationJob | None,
    variant: MediaVariant | None,
) -> str | None:
    if processing_job is not None and processing_job.status == MediaProcessingJobStatus.FAILED.value:
        return processing_job.error_message
    if preparation_job is not None and preparation_job.status == MediaPreparationJobStatus.FAILED.value:
        return preparation_job.error_message
    if variant is not None and variant.status == "failed":
        return variant.error_message
    return None


def _streaming_status(
    asset: MediaAsset | None,
    variant: MediaVariant | None,
    package: MediaStreamingPackage | None,
) -> tuple[EpisodePipelineStageStatus, bool, bool, str | None]:
    if not _is_playback_ready(asset, variant):
        return EpisodePipelineStageStatus.NOT_STARTED, False, False, None
    if package is None:
        return EpisodePipelineStageStatus.PENDING, False, False, None

    if variant is None or variant.path is None:
        return EpisodePipelineStageStatus.PENDING, False, False, None

    if (
        package.source_path != variant.path
        or package.source_variant_updated_at != variant.updated_at
    ):
        return EpisodePipelineStageStatus.PENDING, False, False, None

    status = MediaStreamingPackageStatus(package.status)
    hls_ready = package.hls_master_key is not None
    dash_ready = package.dash_manifest_key is not None

    if status is MediaStreamingPackageStatus.FAILED:
        return (
            EpisodePipelineStageStatus.FAILED,
            hls_ready,
            dash_ready,
            package.error_message,
        )
    if status is MediaStreamingPackageStatus.PROCESSING:
        return (
            EpisodePipelineStageStatus.PROCESSING,
            hls_ready,
            dash_ready,
            package.error_message,
        )
    if status is MediaStreamingPackageStatus.PENDING:
        return (
            EpisodePipelineStageStatus.PENDING,
            hls_ready,
            dash_ready,
            package.error_message,
        )
    if hls_ready and dash_ready:
        return EpisodePipelineStageStatus.COMPLETED, True, True, None
    return EpisodePipelineStageStatus.PENDING, hls_ready, dash_ready, package.error_message


def _current_stage(
    *,
    download_status: EpisodePipelineStageStatus,
    processing_status: EpisodePipelineStageStatus,
    thumbnail_status: EpisodePipelineStageStatus,
    streaming_status: EpisodePipelineStageStatus,
) -> EpisodePipelineCurrentStage | None:
    if download_status in {
        EpisodePipelineStageStatus.PENDING,
        EpisodePipelineStageStatus.DOWNLOADING,
    }:
        return EpisodePipelineCurrentStage.DOWNLOAD
    if processing_status in {
        EpisodePipelineStageStatus.PENDING,
        EpisodePipelineStageStatus.PROCESSING,
    }:
        return EpisodePipelineCurrentStage.PROCESSING
    if thumbnail_status in {
        EpisodePipelineStageStatus.PENDING,
        EpisodePipelineStageStatus.PROCESSING,
    }:
        return EpisodePipelineCurrentStage.PREVIEW
    if streaming_status in {
        EpisodePipelineStageStatus.PENDING,
        EpisodePipelineStageStatus.PROCESSING,
    }:
        return EpisodePipelineCurrentStage.STREAMING
    return None


def _latest_download_jobs(
    rows: Iterable[DownloadJob],
) -> dict[UUID, DownloadJob]:
    result: dict[UUID, DownloadJob] = {}
    for row in rows:
        if row.episode_id not in result:
            result[row.episode_id] = row
    return result


def _latest_processing_jobs(
    rows: Iterable[MediaProcessingJob],
) -> dict[UUID, MediaProcessingJob]:
    result: dict[UUID, MediaProcessingJob] = {}
    for row in rows:
        if row.episode_id not in result:
            result[row.episode_id] = row
    return result


def _latest_preparation_jobs(
    rows: Iterable[MediaPreparationJob],
) -> dict[UUID, MediaPreparationJob]:
    result: dict[UUID, MediaPreparationJob] = {}
    for row in rows:
        if row.media_asset_id not in result:
            result[row.media_asset_id] = row
    return result
