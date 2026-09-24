from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import MediaAttachmentStatus, SubtitleTrackStatus
from .exceptions import MediaAssetValidationError
from .metadata import (
    MediaAssetMetadata,
    MediaAttachmentMetadata,
    MediaChapterMetadata,
    SubtitleTrackMetadata,
)
from .models import MediaAsset, MediaFont
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

    async def retry_failed_attachments(self, asset_id: UUID) -> MediaAsset:
        asset = await self.assets.get(asset_id)
        if asset is None:
            raise MediaAssetValidationError(f"Media asset not found: {asset_id}")

        for attachment in asset.attachments:
            if attachment.processing_status is MediaAttachmentStatus.FAILED:
                attachment.retry()

        asset.attachments_processed_at = None
        return asset

    async def get_or_create_font(
        self,
        *,
        name: str,
        mime_type: str | None,
        sha256: str,
        path: str,
        size_bytes: int,
    ) -> MediaFont:
        font = await self.assets.get_font_by_sha256(sha256)
        if font is not None:
            # The object key can change as storage backends are migrated. The
            # font content is content-addressed, so an existing font row can
            # safely be refreshed to the key just uploaded by the caller.
            font.name = name
            font.mime_type = mime_type
            font.path = path
            font.size_bytes = size_bytes
            return font

        font = MediaFont(
            name=name,
            mime_type=mime_type,
            sha256=sha256,
            path=path,
            size_bytes=size_bytes,
        )
        try:
            async with self.session.begin_nested():
                return await self.assets.add_font(font)
        except IntegrityError:
            existing = await self.assets.get_font_by_sha256(sha256)
            if existing is None:
                raise
            existing.name = name
            existing.mime_type = mime_type
            existing.path = path
            existing.size_bytes = size_bytes
            return existing

    async def upsert(
        self,
        *,
        episode_id: UUID,
        processing_job_id: UUID,
        media_path: str,
        metadata: MediaAssetMetadata,
        subtitle_tracks: tuple[SubtitleTrackMetadata, ...] = (),
        chapters: tuple[MediaChapterMetadata, ...] = (),
        attachments: tuple[MediaAttachmentMetadata, ...] = (),
    ) -> MediaAsset:
        asset = await self.assets.get_for_episode(episode_id)
        if asset is None:
            asset = MediaAsset(episode_id=episode_id)
            asset.processing_job_id = processing_job_id
            asset.path = media_path
            asset.update_metadata(metadata)
            asset.update_subtitle_tracks(subtitle_tracks)
            asset.update_chapters(chapters)
            asset.update_attachments(attachments)
            await self.assets.add(asset)
            return asset

        asset.processing_job_id = processing_job_id
        asset.path = media_path
        asset.update_metadata(metadata)
        asset.update_subtitle_tracks(subtitle_tracks)
        asset.update_chapters(chapters)
        asset.update_attachments(attachments)
        return asset
