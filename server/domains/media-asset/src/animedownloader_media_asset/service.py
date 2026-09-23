from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import SubtitleTrackStatus
from .exceptions import MediaAssetValidationError
from .metadata import MediaAssetMetadata, SubtitleTrackMetadata
from .models import MediaAsset
from .repository import MediaAssetRepository


class MediaAssetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assets = MediaAssetRepository(session)

    async def get(self, asset_id: UUID) -> MediaAsset | None:
        return await self.assets.get(asset_id)

    async def get_for_episode(self, episode_id: UUID) -> MediaAsset | None:
        return await self.assets.get_for_episode(episode_id)

    async def retry_failed_subtitle_tracks(self, asset_id: UUID) -> MediaAsset:
        asset = await self.assets.get(asset_id)
        if asset is None:
            raise MediaAssetValidationError(f"Media asset not found: {asset_id}")

        for track in asset.subtitle_tracks:
            if track.processing_status is SubtitleTrackStatus.FAILED:
                track.retry()

        asset.subtitle_tracks_processed_at = None
        return asset

    async def upsert(
        self,
        *,
        episode_id: UUID,
        processing_job_id: UUID,
        media_path: str,
        metadata: MediaAssetMetadata,
        subtitle_tracks: tuple[SubtitleTrackMetadata, ...] = (),
    ) -> MediaAsset:
        asset = await self.assets.get_for_episode(episode_id)
        if asset is None:
            asset = MediaAsset(
                episode_id=episode_id,
            )
            asset.processing_job_id = processing_job_id
            asset.path = media_path
            asset.update_metadata(metadata)
            asset.update_subtitle_tracks(subtitle_tracks)
            await self.assets.add(asset)
            return asset

        asset.processing_job_id = processing_job_id
        asset.path = media_path
        asset.update_metadata(metadata)
        asset.update_subtitle_tracks(subtitle_tracks)
        return asset
