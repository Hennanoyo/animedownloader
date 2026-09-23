from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from animedownloader_media import FFmpegSubtitleProcessor
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from animedownloader_media_asset import MediaAssetService, SubtitleTrack, SubtitleTrackStatus

logger = logging.getLogger(__name__)


class SubtitleProcessingExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SubtitleTrackContext:
    id: UUID
    stream_index: int | None
    codec_name: str | None
    source_path: str | None
    status: SubtitleTrackStatus


@dataclass(frozen=True, slots=True)
class SubtitleProcessingContext:
    asset_id: UUID
    media_path: str
    tracks: tuple[SubtitleTrackContext, ...]
    ready: bool


class SubtitleProcessingStateProtocol(Protocol):
    async def load(self, asset_id: UUID) -> SubtitleProcessingContext: ...

    async def mark_processing(self, track_id: UUID) -> None: ...

    async def mark_completed(
        self,
        track_id: UUID,
        *,
        normalized_path: str,
        normalized_format: str,
    ) -> None: ...

    async def mark_failed(self, track_id: UUID, *, error_message: str) -> None: ...

    async def mark_asset_complete(self, asset_id: UUID) -> None: ...


class SubtitleProcessingState:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, asset_id: UUID) -> SubtitleProcessingContext:
        async with self._session_factory() as session:
            asset = await MediaAssetService(session).get(asset_id)
            if asset is None:
                raise SubtitleProcessingExecutionError(
                    f"Media asset does not exist: {asset_id}",
                )

            tracks = tuple(
                SubtitleTrackContext(
                    id=track.id,
                    stream_index=track.stream_index,
                    codec_name=track.codec_name,
                    source_path=track.source_path,
                    status=track.processing_status,
                )
                for track in asset.subtitle_tracks
            )
            return SubtitleProcessingContext(
                asset_id=asset.id,
                media_path=asset.path,
                tracks=tracks,
                ready=asset.subtitle_processing_ready,
            )

    async def mark_processing(self, track_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            track = await session.get(SubtitleTrack, track_id)
            if track is None:
                raise SubtitleProcessingExecutionError(
                    f"Subtitle track does not exist: {track_id}",
                )
            track.mark_processing()

    async def mark_completed(
        self,
        track_id: UUID,
        *,
        normalized_path: str,
        normalized_format: str,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            track = await session.get(SubtitleTrack, track_id)
            if track is None:
                raise SubtitleProcessingExecutionError(
                    f"Subtitle track does not exist: {track_id}",
                )
            track.mark_completed(
                normalized_path=normalized_path,
                normalized_format=normalized_format,
            )

    async def mark_failed(self, track_id: UUID, *, error_message: str) -> None:
        async with self._session_factory() as session, session.begin():
            track = await session.get(SubtitleTrack, track_id)
            if track is None:
                raise SubtitleProcessingExecutionError(
                    f"Subtitle track does not exist: {track_id}",
                )
            track.mark_failed(error_message)

    async def mark_asset_complete(self, asset_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            asset = await MediaAssetService(session).get(asset_id)
            if asset is None:
                raise SubtitleProcessingExecutionError(
                    f"Media asset does not exist: {asset_id}",
                )
            asset.mark_subtitle_processing_complete()


class SubtitleProcessingRunner:
    def __init__(
        self,
        *,
        state: SubtitleProcessingStateProtocol,
        processor: FFmpegSubtitleProcessor,
        media_root: Path,
    ) -> None:
        self._state = state
        self._processor = processor
        self._media_root = media_root

    async def run(self, asset_id: UUID) -> None:
        context = await self._state.load(asset_id)
        if context.ready:
            return

        for track in context.tracks:
            if track.status is SubtitleTrackStatus.COMPLETED:
                continue

            await self._state.mark_processing(track.id)
            try:
                normalized_path = _normalized_path(
                    self._media_root,
                    context.asset_id,
                    track.id,
                    track.codec_name,
                )
                if track.source_path is not None:
                    normalized_format = await self._processor.normalize_external(
                        source_path=Path(track.source_path),
                        codec_name=track.codec_name,
                        output_path=normalized_path,
                    )
                else:
                    if track.stream_index is None:
                        raise SubtitleProcessingExecutionError(
                            f"Embedded subtitle track has no stream index: {track.id}",
                        )
                    normalized_format = await self._processor.extract(
                        media_path=Path(context.media_path),
                        stream_index=track.stream_index,
                        codec_name=track.codec_name,
                        output_path=normalized_path,
                    )
                await self._state.mark_completed(
                    track.id,
                    normalized_path=str(normalized_path),
                    normalized_format=normalized_format,
                )
            except Exception as exc:
                await self._state.mark_failed(
                    track.id,
                    error_message=_format_error(exc),
                )
                logger.exception(
                    "Subtitle processing failed for track %s",
                    track.id,
                )

        await self._state.mark_asset_complete(context.asset_id)


def _normalized_path(
    media_root: Path,
    asset_id: UUID,
    track_id: UUID,
    codec_name: str | None,
) -> Path:
    extension = "ssa" if (codec_name or "").casefold() == "ssa" else "ass"
    return media_root / "subtitles" / str(asset_id) / f"{track_id}.{extension}"


def _format_error(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    return message[:2000]


def create_subtitle_processing_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> SubtitleProcessingState:
    return SubtitleProcessingState(session_factory)
