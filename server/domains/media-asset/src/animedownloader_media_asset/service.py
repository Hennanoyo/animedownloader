from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .metadata import MediaAssetMetadata
from .models import MediaAsset
from .repository import MediaAssetRepository


class MediaAssetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assets = MediaAssetRepository(session)

    async def get_for_episode(self, episode_id: UUID) -> MediaAsset | None:
        return await self.assets.get_for_episode(episode_id)

    async def upsert(
        self,
        *,
        episode_id: UUID,
        processing_job_id: UUID,
        media_path: str,
        metadata: MediaAssetMetadata,
    ) -> MediaAsset:
        asset = await self.assets.get_for_episode(episode_id)
        if asset is None:
            asset = MediaAsset(
                episode_id=episode_id,
            )
            asset.processing_job_id = processing_job_id
            asset.path = media_path
            asset.update_metadata(metadata)
            await self.assets.add(asset)
            return asset

        asset.processing_job_id = processing_job_id
        asset.path = media_path
        asset.update_metadata(metadata)
        return asset
