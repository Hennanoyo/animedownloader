from collections.abc import AsyncIterator
from typing import Annotated

from animedownloader_anime import AnimeService
from animedownloader_database import Database
from animedownloader_download import DownloadJobService

from animedownloader_api.task_queue import DownloadTaskDispatcher
from animedownloader_nyaa import NyaaClient
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

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


async def get_nyaa_client() -> AsyncIterator[NyaaClient]:
    yield NyaaClient()
