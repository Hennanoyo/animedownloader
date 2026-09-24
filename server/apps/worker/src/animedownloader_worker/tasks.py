import logging
from uuid import UUID

from animedownloader_config import Settings
from animedownloader_database import Database, create_database
from animedownloader_download import DOWNLOAD_TASK_NAME, DownloadJobService
from animedownloader_media import (
    FFmpegAttachmentProcessor,
    FFmpegCMAFProcessor,
    FFmpegMediaPreparationProcessor,
    FFmpegPlayableMediaProcessor,
    FFmpegSubtitleProcessor,
    FFmpegThumbnailSpriteProcessor,
    FFprobeInspector,
    PlayableMediaPlanner,
    SubprocessFFmpegRunner,
)
from animedownloader_media_asset import (
    MEDIA_ATTACHMENT_PROCESSING_TASK_NAME,
    SUBTITLE_PROCESSING_TASK_NAME,
    MediaAssetService,
)
from animedownloader_media_processing import (
    MEDIA_PACKAGING_TASK_NAME,
    MEDIA_PREPARATION_TASK_NAME,
    MEDIA_PROCESSING_TASK_NAME,
    MediaPreparationJobService,
    MediaProcessingJobService,
    MediaProcessingJobStatus,
    MediaStreamingPackageService,
    MediaVariantService,
)
from animedownloader_qbittorrent import QBittorrentClient

from .broker import broker
from .media_attachment_processing import (
    MediaAttachmentProcessingRunner,
    create_media_attachment_processing_state,
)
from .media_packaging import MediaPackagingRunner, create_media_packaging_state
from .media_preparation import MediaPreparationRunner, create_media_preparation_state
from .media_processing import MediaProcessingRunner, create_media_processing_state
from .runner import DownloadRunner, create_download_state
from .storage import create_media_storage
from .subtitle_processing import (
    SubtitleProcessingRunner,
    create_subtitle_processing_state,
)


logger = logging.getLogger(__name__)


@broker.task(task_name=DOWNLOAD_TASK_NAME)
async def download_episode(job_id: str) -> None:
    logger.info("Download task started: job_id=%s", job_id)
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        api_key = (
            settings.qbittorrent_api_key.get_secret_value()
            if settings.qbittorrent_api_key is not None
            else ""
        )
        async with QBittorrentClient(
            settings.qbittorrent_url,
            api_key,
        ) as torrent_client:
            runner = DownloadRunner(
                state=create_download_state(database),
                torrent_client=torrent_client,
                download_root=settings.download_root,
                on_completed=lambda completed_job_id: _enqueue_media_processing(
                    database,
                    completed_job_id,
                ),
            )
            await runner.run(UUID(job_id))
            logger.info("Download task completed: job_id=%s", job_id)
    finally:
        await database.dispose()


@broker.task(task_name=MEDIA_PROCESSING_TASK_NAME)
async def process_media_job(job_id: str) -> None:
    logger.info("Media processing task started: job_id=%s", job_id)
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        runner = MediaProcessingRunner(
            state=create_media_processing_state(database.session_factory),
            inspector=FFprobeInspector(),
            download_root=settings.download_root,
        )
        parsed_job_id = UUID(job_id)
        await runner.run(parsed_job_id)
        await _enqueue_subtitle_processing(database, parsed_job_id)
        await _enqueue_media_attachment_processing(database, parsed_job_id)
        await _enqueue_media_preparation(database, parsed_job_id)
        logger.info("Media processing task completed: job_id=%s", job_id)
    finally:
        await database.dispose()


@broker.task(task_name=SUBTITLE_PROCESSING_TASK_NAME)
async def process_subtitle_tracks(asset_id: str) -> None:
    logger.info("Subtitle processing task started: asset_id=%s", asset_id)
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        ffmpeg_runner = SubprocessFFmpegRunner(
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        runner = SubtitleProcessingRunner(
            state=create_subtitle_processing_state(database.session_factory),
            storage=create_media_storage(settings),
            processor=FFmpegSubtitleProcessor(runner=ffmpeg_runner),
        )
        await runner.run(UUID(asset_id))
        logger.info("Subtitle processing task completed: asset_id=%s", asset_id)
    finally:
        await database.dispose()


async def _enqueue_subtitle_processing(
    database: Database,
    job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        job = await MediaProcessingJobService(session).get_job(job_id)
        asset = await MediaAssetService(session).get_for_episode(job.episode_id)

    if asset is None or asset.subtitle_processing_ready:
        return

    await process_subtitle_tracks.kiq(str(asset.id))


async def _enqueue_media_processing(
    database: Database,
    download_job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        download_job = await DownloadJobService(session).get_job(download_job_id)
        media_service = MediaProcessingJobService(session)
        job = await media_service.create_job(
            download_job.episode_id,
            download_job.id,
        )

    if job.job_status is MediaProcessingJobStatus.COMPLETED:
        return

    await process_media_job.kiq(str(job.id))


@broker.task(task_name=MEDIA_ATTACHMENT_PROCESSING_TASK_NAME)
async def process_media_attachments(asset_id: str) -> None:
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        ffmpeg_runner = SubprocessFFmpegRunner(
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        runner = MediaAttachmentProcessingRunner(
            state=create_media_attachment_processing_state(database.session_factory),
            storage=create_media_storage(settings),
            processor=FFmpegAttachmentProcessor(runner=ffmpeg_runner),
        )
        await runner.run(UUID(asset_id))
    finally:
        await database.dispose()


async def _enqueue_media_attachment_processing(
    database: Database,
    job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        job = await MediaProcessingJobService(session).get_job(job_id)
        asset = await MediaAssetService(session).get_for_episode(job.episode_id)

    if asset is None or not asset.attachments_ready or asset.attachment_processing_ready:
        return

    await process_media_attachments.kiq(str(asset.id))


@broker.task(task_name=MEDIA_PREPARATION_TASK_NAME)
async def process_media_preparation(job_id: str) -> None:
    logger.info("Media preparation task started: job_id=%s", job_id)
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        ffmpeg_runner = SubprocessFFmpegRunner(
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        runner = MediaPreparationRunner(
            state=create_media_preparation_state(database.session_factory),
            storage=create_media_storage(settings),
            inspector=FFprobeInspector(),
            planner=PlayableMediaPlanner(),
            preparation_processor=FFmpegMediaPreparationProcessor(
                runner=ffmpeg_runner,
            ),
            playable_processor=FFmpegPlayableMediaProcessor(
                runner=ffmpeg_runner,
            ),
            thumbnail_processor=FFmpegThumbnailSpriteProcessor(
                runner=ffmpeg_runner,
            ),
        )
        parsed_job_id = UUID(job_id)
        await runner.run(parsed_job_id)
        await _enqueue_media_packaging(database, parsed_job_id)
        logger.info("Media preparation task completed: job_id=%s", job_id)
    finally:
        await database.dispose()


async def _enqueue_media_preparation(
    database: Database,
    media_processing_job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        processing_job = await MediaProcessingJobService(session).get_job(
            media_processing_job_id,
        )
        asset = await MediaAssetService(session).get_for_episode(
            processing_job.episode_id,
        )
        if asset is None or asset.metadata_updated_at is None:
            return

        preparation_job = await MediaPreparationJobService(session).create_job(
            media_asset_id=asset.id,
            source_path=asset.path,
            source_metadata_updated_at=asset.metadata_updated_at,
            thumbnail_ready=asset.thumbnail_ready,
        )

    if preparation_job is None:
        logger.info(
            "Media preparation task not enqueued: an active job already exists "
            "or the asset is already prepared: asset_id=%s",
            asset.id,
        )
        return

    logger.info(
        "Enqueuing media preparation task: job_id=%s asset_id=%s",
        preparation_job.id,
        asset.id,
    )
    await process_media_preparation.kiq(str(preparation_job.id))


@broker.task(task_name=MEDIA_PACKAGING_TASK_NAME)
async def process_media_packaging(job_id: str) -> None:
    logger.info("Media packaging task started: job_id=%s", job_id)
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        ffmpeg_runner = SubprocessFFmpegRunner(
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        runner = MediaPackagingRunner(
            state=create_media_packaging_state(database.session_factory),
            storage=create_media_storage(settings),
            processor=FFmpegCMAFProcessor(runner=ffmpeg_runner),
        )
        parsed_job_id = UUID(job_id)
        await runner.run(parsed_job_id)
        logger.info("Media packaging task completed: job_id=%s", job_id)
    finally:
        await database.dispose()


async def _enqueue_media_packaging(
    database: Database,
    media_preparation_job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        preparation_job = await MediaPreparationJobService(session).get_job(
            media_preparation_job_id,
        )
        variant = await MediaVariantService(session).get_playable_variant(
            preparation_job.variant_id,
        )
        if variant is None:
            return

        packaging_job = await MediaStreamingPackageService(session).create_job(
            media_variant_id=variant.id,
        )

    if packaging_job is None:
        return

    await process_media_packaging.kiq(str(packaging_job.id))
