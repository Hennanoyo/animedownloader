from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from animedownloader_media import (
    FFmpegThumbnailSpriteProcessor,
    ThumbnailSpriteResult,
)
from animedownloader_media_asset import MediaAssetService, MediaThumbnailStatus
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class MediaThumbnailProcessingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaThumbnailProcessingContext:
    asset_id: UUID
    media_path: str
    duration_seconds: float | None
    status: MediaThumbnailStatus
    ready: bool


class MediaThumbnailProcessingStateProtocol(Protocol):
    async def load(self, asset_id: UUID) -> MediaThumbnailProcessingContext: ...

    async def mark_processing(self, asset_id: UUID) -> None: ...

    async def mark_completed(
        self,
        asset_id: UUID,
        *,
        result: ThumbnailSpriteResult,
    ) -> None: ...

    async def mark_failed(self, asset_id: UUID, *, error_message: str) -> None: ...


class MediaThumbnailProcessingState:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, asset_id: UUID) -> MediaThumbnailProcessingContext:
        async with self._session_factory() as session:
            asset = await MediaAssetService(session).get(asset_id)
            if asset is None:
                raise MediaThumbnailProcessingError(
                    f"Media asset does not exist: {asset_id}",
                )
            return MediaThumbnailProcessingContext(
                asset_id=asset.id,
                media_path=asset.path,
                duration_seconds=asset.duration_seconds,
                status=asset.thumbnail_processing_status,
                ready=asset.thumbnail_ready,
            )

    async def mark_processing(self, asset_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            asset = await MediaAssetService(session).get(asset_id)
            if asset is None:
                raise MediaThumbnailProcessingError(
                    f"Media asset does not exist: {asset_id}",
                )
            asset.mark_thumbnail_processing()

    async def mark_completed(
        self,
        asset_id: UUID,
        *,
        result: ThumbnailSpriteResult,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            asset = await MediaAssetService(session).get(asset_id)
            if asset is None:
                raise MediaThumbnailProcessingError(
                    f"Media asset does not exist: {asset_id}",
                )
            asset.mark_thumbnail_completed(
                sprite_path=str(result.sprite_path),
                vtt_path=str(result.vtt_path),
            )

    async def mark_failed(self, asset_id: UUID, *, error_message: str) -> None:
        async with self._session_factory() as session, session.begin():
            asset = await MediaAssetService(session).get(asset_id)
            if asset is None:
                raise MediaThumbnailProcessingError(
                    f"Media asset does not exist: {asset_id}",
                )
            asset.mark_thumbnail_failed(error_message)


class MediaThumbnailProcessingRunner:
    def __init__(
        self,
        *,
        state: MediaThumbnailProcessingStateProtocol,
        processor: FFmpegThumbnailSpriteProcessor,
        media_root: Path,
    ) -> None:
        self._state = state
        self._processor = processor
        self._media_root = media_root

    async def run(self, asset_id: UUID) -> None:
        context = await self._state.load(asset_id)
        if context.ready:
            return

        await self._state.mark_processing(asset_id)

        try:
            output_dir = self._media_root / "thumbnails" / str(asset_id)
            result = await self._processor.generate(
                media_path=Path(context.media_path),
                output_dir=output_dir,
                duration_seconds=context.duration_seconds,
            )
            await self._state.mark_completed(
                asset_id,
                result=result,
            )
        except Exception as exc:
            await self._state.mark_failed(
                asset_id,
                error_message=_format_error(exc),
            )
            logger.exception(
                "Media thumbnail processing failed for asset %s",
                asset_id,
            )


def _format_error(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    return message[:2000]


def create_media_thumbnail_processing_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> MediaThumbnailProcessingState:
    return MediaThumbnailProcessingState(session_factory)
