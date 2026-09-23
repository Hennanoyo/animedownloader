from collections.abc import AsyncIterator
from typing import Annotated

from animedownloader_anime import AnimeService
from animedownloader_config import Settings
from animedownloader_database import Database
from animedownloader_download import DownloadJobService
from animedownloader_media_processing import MediaProcessingJobService
from animedownloader_nyaa import NyaaClient
from animedownloader_qbittorrent import QBittorrentClient
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from animedownloader_api.media_processing_queue import MediaProcessingTaskDispatcher
from animedownloader_api.task_queue import DownloadTaskDispatcher


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session_factory() as session:
        yield session


def get_anime_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnimeService:
    return AnimeService(session)


def get_download_job_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DownloadJobService:
    return DownloadJobService(session)


def get_download_task_dispatcher(request: Request) -> DownloadTaskDispatcher:
    return request.app.state.download_task_dispatcher


def get_media_processing_job_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MediaProcessingJobService:
    return MediaProcessingJobService(session)


def get_media_processing_task_dispatcher(
    request: Request,
) -> MediaProcessingTaskDispatcher:
    return request.app.state.media_processing_task_dispatcher


async def get_nyaa_client() -> AsyncIterator[NyaaClient]:
    async with NyaaClient() as client:
        yield client



async def get_qbittorrent_client(
    request: Request,
) -> AsyncIterator[QBittorrentClient]:
    settings: Settings = request.app.state.settings
    api_key = (
        settings.qbittorrent_api_key.get_secret_value()
        if settings.qbittorrent_api_key
        else ""
    )
    async with QBittorrentClient(settings.qbittorrent_url, api_key) as client:
        yield client
