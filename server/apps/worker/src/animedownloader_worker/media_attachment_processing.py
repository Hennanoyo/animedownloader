from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol
from uuid import UUID

from animedownloader_media import FFmpegAttachmentProcessor
from animedownloader_media_asset import (
    MediaAssetService,
    MediaAttachment,
    MediaAttachmentStatus,
)
from animedownloader_storage import AttachmentArtifact, FontArtifact, Storage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class MediaAttachmentProcessingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaAttachmentContext:
    id: UUID
    attachment_index: int
    filename: str | None
    mime_type: str | None
    is_font: bool
    status: MediaAttachmentStatus


@dataclass(frozen=True, slots=True)
class MediaAttachmentProcessingContext:
    asset_id: UUID
    media_path: str
    attachments: tuple[MediaAttachmentContext, ...]
    ready: bool


class MediaAttachmentProcessingStateProtocol(Protocol):
    async def load(self, asset_id: UUID) -> MediaAttachmentProcessingContext: ...

    async def mark_processing(self, attachment_id: UUID) -> None: ...

    async def mark_completed(
        self,
        attachment_id: UUID,
        *,
        extracted_path: str,
        size_bytes: int,
        font_id: UUID | None = None,
    ) -> None: ...

    async def mark_failed(
        self,
        attachment_id: UUID,
        *,
        error_message: str,
    ) -> None: ...

    async def mark_asset_complete(self, asset_id: UUID) -> None: ...

    async def get_or_create_font(
        self,
        *,
        name: str,
        mime_type: str | None,
        sha256: str,
        path: str,
        size_bytes: int,
    ) -> UUID: ...


class MediaAttachmentProcessingState:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, asset_id: UUID) -> MediaAttachmentProcessingContext:
        async with self._session_factory() as session:
            asset = await MediaAssetService(session).get(asset_id)
            if asset is None:
                raise MediaAttachmentProcessingError(
                    f"Media asset does not exist: {asset_id}",
                )
            return MediaAttachmentProcessingContext(
                asset_id=asset.id,
                media_path=asset.path,
                attachments=tuple(
                    MediaAttachmentContext(
                        id=attachment.id,
                        attachment_index=attachment.attachment_index,
                        filename=attachment.filename,
                        mime_type=attachment.mime_type,
                        is_font=attachment.is_font,
                        status=attachment.processing_status,
                    )
                    for attachment in asset.attachments
                ),
                ready=asset.attachment_processing_ready,
            )

    async def mark_processing(self, attachment_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            attachment = await session.get(MediaAttachment, attachment_id)
            if attachment is None:
                raise MediaAttachmentProcessingError(
                    f"Media attachment does not exist: {attachment_id}",
                )
            attachment.mark_processing()

    async def mark_completed(
        self,
        attachment_id: UUID,
        *,
        extracted_path: str,
        size_bytes: int,
        font_id: UUID | None = None,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            attachment = await session.get(MediaAttachment, attachment_id)
            if attachment is None:
                raise MediaAttachmentProcessingError(
                    f"Media attachment does not exist: {attachment_id}",
                )
            attachment.mark_completed(
                extracted_path=extracted_path,
                size_bytes=size_bytes,
                font_id=font_id,
            )

    async def mark_failed(
        self,
        attachment_id: UUID,
        *,
        error_message: str,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            attachment = await session.get(MediaAttachment, attachment_id)
            if attachment is None:
                raise MediaAttachmentProcessingError(
                    f"Media attachment does not exist: {attachment_id}",
                )
            attachment.mark_failed(error_message)

    async def mark_asset_complete(self, asset_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            asset = await MediaAssetService(session).get(asset_id)
            if asset is None:
                raise MediaAttachmentProcessingError(
                    f"Media asset does not exist: {asset_id}",
                )
            asset.mark_attachment_processing_complete()

    async def get_or_create_font(
        self,
        *,
        name: str,
        mime_type: str | None,
        sha256: str,
        path: str,
        size_bytes: int,
    ) -> UUID:
        async with self._session_factory() as session, session.begin():
            service = MediaAssetService(session)
            font = await service.get_or_create_font(
                name=name,
                mime_type=mime_type,
                sha256=sha256,
                path=path,
                size_bytes=size_bytes,
            )
            return font.id


class MediaAttachmentProcessingRunner:
    def __init__(
        self,
        *,
        state: MediaAttachmentProcessingStateProtocol,
        processor: FFmpegAttachmentProcessor,
        storage: Storage,
    ) -> None:
        self._state = state
        self._processor = processor
        self._storage = storage

    async def run(self, asset_id: UUID) -> None:
        context = await self._state.load(asset_id)
        if context.ready:
            return

        with TemporaryDirectory(prefix="animedownloader-attachments-") as staging_dir:
            staging_root = Path(staging_dir)
            for attachment in context.attachments:
                if attachment.status is MediaAttachmentStatus.COMPLETED:
                    continue

                await self._state.mark_processing(attachment.id)
                output_path = self._output_path(
                    staging_root,
                    context.asset_id,
                    attachment,
                )

                try:
                    await self._processor.extract(
                        media_path=Path(context.media_path),
                        attachment_index=attachment.attachment_index,
                        output_path=output_path,
                    )
                    size_bytes = output_path.stat().st_size
                    font_id = None
                    filename = output_path.name

                    if attachment.is_font:
                        sha256 = _sha256(output_path)
                        extension = output_path.suffix or ".bin"
                        object_key = FontArtifact(
                            sha256=sha256,
                            extension=extension,
                        ).object_key
                        await self._storage.put_file(
                            output_path,
                            object_key,
                            content_type=attachment.mime_type,
                        )
                        font_id = await self._state.get_or_create_font(
                            name=attachment.filename or filename,
                            mime_type=attachment.mime_type,
                            sha256=sha256,
                            path=object_key,
                            size_bytes=size_bytes,
                        )
                    else:
                        extension = Path(filename).suffix.lstrip(".") or "bin"
                        object_key = AttachmentArtifact(
                            asset_id=context.asset_id,
                            attachment_id=attachment.id,
                            extension=extension,
                        ).object_key
                        await self._storage.put_file(
                            output_path,
                            object_key,
                            content_type=attachment.mime_type,
                        )

                    await self._state.mark_completed(
                        attachment.id,
                        extracted_path=object_key,
                        size_bytes=size_bytes,
                        font_id=font_id,
                    )
                except Exception as exc:
                    await self._state.mark_failed(
                        attachment.id,
                        error_message=_format_error(exc),
                    )
                    logger.exception(
                        "Media attachment processing failed for attachment %s",
                        attachment.id,
                    )

        await self._state.mark_asset_complete(context.asset_id)

    def _output_path(
        self,
        root: Path,
        asset_id: UUID,
        attachment: MediaAttachmentContext,
    ) -> Path:
        filename = Path(
            attachment.filename or f"attachment-{attachment.attachment_index}",
        ).name
        return root / "attachments" / str(asset_id) / f"{attachment.id}-{filename}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _format_error(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    return message[:2000]


def create_media_attachment_processing_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> MediaAttachmentProcessingState:
    return MediaAttachmentProcessingState(session_factory)
