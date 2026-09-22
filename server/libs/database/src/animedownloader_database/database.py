from dataclasses import dataclass
from typing import Self

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(slots=True)
class Database:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

    @classmethod
    def from_url(cls, database_url: str) -> Self:
        engine = create_async_engine(database_url, pool_pre_ping=True)
        return cls(
            engine=engine,
            session_factory=async_sessionmaker(
                engine,
                expire_on_commit=False,
            ),
        )

    async def dispose(self) -> None:
        await self.engine.dispose()


def create_database(database_url: str) -> Database:
    return Database.from_url(database_url)
