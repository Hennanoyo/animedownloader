from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Anime, Episode


class AnimeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> list[Anime]:
        result = await self.session.scalars(
            select(Anime).order_by(Anime.year.desc(), Anime.title.asc())
        )
        return list(result.all())

    async def get(self, anime_id: UUID) -> Anime | None:
        return await self.session.get(Anime, anime_id)

    async def add(self, anime: Anime) -> Anime:
        self.session.add(anime)
        await self.session.flush()
        return anime

    async def delete(self, anime: Anime) -> None:
        await self.session.delete(anime)


class EpisodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_anime(self, anime_id: UUID) -> list[Episode]:
        result = await self.session.scalars(
            select(Episode)
            .where(Episode.anime_id == anime_id)
            .order_by(Episode.episode_number.asc())
        )
        return list(result.all())

    async def get(self, episode_id: UUID) -> Episode | None:
        return await self.session.get(Episode, episode_id)

    async def exists_number(
        self,
        anime_id: UUID,
        episode_number: int,
        *,
        exclude_episode_id: UUID | None = None,
    ) -> bool:
        statement = select(Episode.id).where(
            Episode.anime_id == anime_id,
            Episode.episode_number == episode_number,
        )
        if exclude_episode_id is not None:
            statement = statement.where(Episode.id != exclude_episode_id)
        return await self.session.scalar(statement) is not None

    async def add(self, episode: Episode) -> Episode:
        self.session.add(episode)
        await self.session.flush()
        return episode

    async def delete(self, episode: Episode) -> None:
        await self.session.delete(episode)
