from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import MediaAsset


class MediaAssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_episode(self, episode_id: UUID) -> MediaAsset | None:
        return await self.session.scalar(
            select(MediaAsset)
            .options(selectinload(MediaAsset.subtitle_tracks))
            .where(MediaAsset.episode_id == episode_id),
        )

    async def get_for_processing_job(self, processing_job_id: UUID) -> MediaAsset | None:
        return await self.session.scalar(
            select(MediaAsset)
            .options(selectinload(MediaAsset.subtitle_tracks))
            .where(
                MediaAsset.processing_job_id == processing_job_id,
            ),
        )

    async def add(self, asset: MediaAsset) -> MediaAsset:
        self.session.add(asset)
        await self.session.flush()
        return asset
