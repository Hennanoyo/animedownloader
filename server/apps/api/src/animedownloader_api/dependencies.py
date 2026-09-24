from collections.abc import AsyncIterator
from typing import Annotated

from animedownloader_anime import AnimeService
from animedownloader_config import Settings
from animedownloader_database import Database
from animedownloader_download import DownloadJobService
from animedownloader_media_asset import MediaAssetService
from animedownloader_media_processing import (
    MediaPreparationJobService,
    MediaProcessingJobService,
    MediaStreamingPackageService,
    MediaVariantService,
)
from animedownloader_nyaa import NyaaClient
from animedownloader_storage import Storage
from animedownloader_qbittorrent import QBittorrentClient
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from animedownloader_api.media_processing_queue import MediaProcessingTaskDispatcher
from animedownloader_api.playback import PlaybackService
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


def get_media_asset_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MediaAssetService:
    return MediaAssetService(session)


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
        settings.qbittorrent_api_key.get_secret_value() if settings.qbittorrent_api_key else ""
    )
    async with QBittorrentClient(settings.qbittorrent_url, api_key) as client:
        yield client


def get_media_preparation_job_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MediaPreparationJobService:
    return MediaPreparationJobService(session)


def get_media_variant_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MediaVariantService:
    return MediaVariantService(session)


def get_media_streaming_package_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MediaStreamingPackageService:
    return MediaStreamingPackageService(session)


def get_media_storage(request: Request) -> Storage:
    return request.app.state.media_storage


def get_playback_service(
    anime_service: Annotated[AnimeService, Depends(get_anime_service)],
    media_asset_service: Annotated[
        MediaAssetService,
        Depends(get_media_asset_service),
    ],
    media_variant_service: Annotated[
        MediaVariantService,
        Depends(get_media_variant_service),
    ],
    streaming_package_service: Annotated[
        MediaStreamingPackageService,
        Depends(get_media_streaming_package_service),
    ],
    storage: Annotated[Storage, Depends(get_media_storage)],
) -> PlaybackService:
    return PlaybackService(
        anime_service=anime_service,
        media_asset_service=media_asset_service,
        media_variant_service=media_variant_service,
        streaming_package_service=streaming_package_service,
        storage=storage,
    )
