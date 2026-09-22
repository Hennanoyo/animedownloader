from collections.abc import AsyncIterator

from animedownloader_anime import AnimeService
from animedownloader_database import Database
from animedownloader_nyaa import NyaaClient
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session_factory() as session:
        yield session


def get_anime_service(
    session: AsyncSession = Depends(get_db_session),
) -> AnimeService:
    return AnimeService(session)


async def get_nyaa_client() -> AsyncIterator[NyaaClient]:
    async with NyaaClient() as client:
        yield client
