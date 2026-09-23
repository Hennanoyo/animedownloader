from uuid import UUID

from animedownloader_config import Settings
from animedownloader_database import create_database
from animedownloader_download import DOWNLOAD_TASK_NAME
from animedownloader_qbittorrent import QBittorrentClient

from .broker import broker
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
            )
            await runner.run(UUID(job_id))
    finally:
        await database.dispose()
