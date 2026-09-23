from uuid import UUID

from animedownloader_config import Settings
from animedownloader_database import Database, create_database
from animedownloader_download import DOWNLOAD_TASK_NAME, DownloadJobService
from animedownloader_media import (
    FFmpegAttachmentProcessor,
    FFmpegPlayableMediaProcessor,
    FFmpegSubtitleProcessor,
    FFmpegThumbnailSpriteProcessor,
    FFprobeInspector,
    PlayableMediaPlanner,
)
from animedownloader_media_asset import (
    MEDIA_ATTACHMENT_PROCESSING_TASK_NAME,
    MEDIA_THUMBNAIL_PROCESSING_TASK_NAME,
    SUBTITLE_PROCESSING_TASK_NAME,
    MediaAssetService,
)
from animedownloader_media_processing import (
    MEDIA_PROCESSING_TASK_NAME,
    MEDIA_TRANSCODING_TASK_NAME,
    MediaProcessingJobService,
    MediaProcessingJobStatus,
    MediaTranscodingJobService,
)
from animedownloader_qbittorrent import QBittorrentClient

from .broker import broker
from .media_attachment_processing import (
    MediaAttachmentProcessingRunner,
    create_media_attachment_processing_state,
)
from .media_processing import MediaProcessingRunner, create_media_processing_state
from .media_transcoding import MediaTranscodingRunner, create_media_transcoding_state
from .media_thumbnail_processing import (
    MediaThumbnailProcessingRunner,
    create_media_thumbnail_processing_state,
)
from .runner import DownloadRunner, create_download_state
from .subtitle_processing import (
    SubtitleProcessingRunner,
    create_subtitle_processing_state,
)


@broker.task(task_name=DOWNLOAD_TASK_NAME)
async def download_episode(job_id: str) -> None:
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
    finally:
        await database.dispose()


@broker.task(task_name=MEDIA_PROCESSING_TASK_NAME)
async def process_media_job(job_id: str) -> None:
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
        await _enqueue_media_thumbnail_processing(database, parsed_job_id)
        await _enqueue_media_transcoding(database, parsed_job_id)
    finally:
        await database.dispose()


@broker.task(task_name=SUBTITLE_PROCESSING_TASK_NAME)
async def process_subtitle_tracks(asset_id: str) -> None:
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        runner = SubtitleProcessingRunner(
            state=create_subtitle_processing_state(database.session_factory),
            processor=FFmpegSubtitleProcessor(),
            media_root=settings.media_root,
        )
        await runner.run(UUID(asset_id))
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
        runner = MediaAttachmentProcessingRunner(
            state=create_media_attachment_processing_state(database.session_factory),
            processor=FFmpegAttachmentProcessor(),
            media_root=settings.media_root,
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


@broker.task(task_name=MEDIA_THUMBNAIL_PROCESSING_TASK_NAME)
async def process_media_thumbnail(asset_id: str) -> None:
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        runner = MediaThumbnailProcessingRunner(
            state=create_media_thumbnail_processing_state(database.session_factory),
            processor=FFmpegThumbnailSpriteProcessor(),
            media_root=settings.media_root,
        )
        await runner.run(UUID(asset_id))
    finally:
        await database.dispose()


async def _enqueue_media_thumbnail_processing(
    database: Database,
    job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        job = await MediaProcessingJobService(session).get_job(job_id)
        asset = await MediaAssetService(session).get_for_episode(job.episode_id)

    if asset is None or asset.thumbnail_ready:
        return

    await process_media_thumbnail.kiq(str(asset.id))

@broker.task(task_name=MEDIA_TRANSCODING_TASK_NAME)
async def process_media_transcoding(job_id: str) -> None:
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        runner = MediaTranscodingRunner(
            state=create_media_transcoding_state(database.session_factory),
            inspector=FFprobeInspector(),
            planner=PlayableMediaPlanner(),
            processor=FFmpegPlayableMediaProcessor(),
            media_root=settings.media_root,
        )
        await runner.run(UUID(job_id))
    finally:
        await database.dispose()


async def _enqueue_media_transcoding(
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

        transcoding_job = await MediaTranscodingJobService(session).create_job(
            media_asset_id=asset.id,
            source_path=asset.path,
            source_metadata_updated_at=asset.metadata_updated_at,
        )

    if transcoding_job is None:
        return

    await process_media_transcoding.kiq(str(transcoding_job.id))