from uuid import UUID

from animedownloader_config import Settings
from animedownloader_database import create_database
from animedownloader_download import DOWNLOAD_TASK_NAME, DownloadJobService
from animedownloader_media import FFprobeInspector
from animedownloader_media_processing import (
    MEDIA_PROCESSING_TASK_NAME,
    MediaProcessingJobService,
)
from animedownloader_qbittorrent import QBittorrentClient

from .broker import broker
from .media_processing import (
    MediaProcessingRunner,
    create_media_processing_state,
)
from .runner import DownloadRunner, create_download_state


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
        await runner.run(UUID(job_id))
    finally:
        await database.dispose()


async def _enqueue_media_processing(
    database,
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
