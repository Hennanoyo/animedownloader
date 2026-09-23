from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .enums import MediaVariantKind
from .models import MediaVariant
from .repository import MediaProcessingJobRepository


class MediaVariantService:
    def __init__(self, session: AsyncSession) -> None:
        self.variants = MediaProcessingJobRepository(session)

    async def get(self, variant_id: UUID) -> MediaVariant | None:
        return await self.variants.get_variant(variant_id)

    async def get_playable_variant(self, media_asset_id: UUID) -> MediaVariant | None:
        return await self.variants.get_playable_variant(media_asset_id)

    async def create_playable_variant(self, media_asset_id: UUID) -> MediaVariant:
        existing = await self.get_playable_variant(media_asset_id)
        if existing is not None:
            return existing

        variant = MediaVariant(
            media_asset_id=media_asset_id,
            kind=MediaVariantKind.PLAYABLE.value,
        )
        return await self.variants.add_variant(variant)
