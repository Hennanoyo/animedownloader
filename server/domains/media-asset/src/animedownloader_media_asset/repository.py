from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import MediaAsset, MediaAttachment, MediaFont, SubtitleTrack


class MediaAssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, asset_id: UUID) -> MediaAsset | None:
        return await self.session.scalar(
            select(MediaAsset)
            .options(
                selectinload(MediaAsset.subtitle_tracks),
                selectinload(MediaAsset.chapters),
                selectinload(MediaAsset.attachments).selectinload(MediaAttachment.font),
            )
            .where(MediaAsset.id == asset_id),
        )

    async def get_for_episode(self, episode_id: UUID) -> MediaAsset | None:
        return await self.session.scalar(
            select(MediaAsset)
            .options(
                selectinload(MediaAsset.subtitle_tracks),
                selectinload(MediaAsset.chapters),
                selectinload(MediaAsset.attachments).selectinload(MediaAttachment.font),
            )
            .where(MediaAsset.episode_id == episode_id),
        )

    async def get_for_processing_job(self, processing_job_id: UUID) -> MediaAsset | None:
        return await self.session.scalar(
            select(MediaAsset)
            .options(
                selectinload(MediaAsset.subtitle_tracks),
                selectinload(MediaAsset.chapters),
                selectinload(MediaAsset.attachments).selectinload(MediaAttachment.font),
            )
            .where(MediaAsset.processing_job_id == processing_job_id),
        )

    async def get_track(self, track_id: UUID) -> SubtitleTrack | None:
        return await self.session.get(SubtitleTrack, track_id)

    async def get_attachment(self, attachment_id: UUID) -> MediaAttachment | None:
        return await self.session.get(MediaAttachment, attachment_id)

    async def get_font_by_sha256(self, sha256: str) -> MediaFont | None:
        return await self.session.scalar(
            select(MediaFont).where(MediaFont.sha256 == sha256),
        )

    async def add(self, asset: MediaAsset) -> MediaAsset:
        self.session.add(asset)
        await self.session.flush()
        return asset

    async def add_font(self, font: MediaFont) -> MediaFont:
        self.session.add(font)
        await self.session.flush()
        return font
