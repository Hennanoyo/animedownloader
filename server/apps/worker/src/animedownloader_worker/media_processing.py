from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Protocol, cast
from uuid import UUID

from animedownloader_media import MediaProbe, MediaStream
from animedownloader_media_asset import MediaAssetMetadata, MediaAssetService
from animedownloader_media_processing import (
    MediaProcessingJobService,
    MediaProcessingJobStatus,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


MEDIA_EXTENSIONS = frozenset(
    {
        ".avi",
        ".flv",
        ".m2ts",
        ".m4v",
        ".mkv",
        ".mov",
        ".mp4",
        ".mpeg",
        ".mpg",
        ".mts",
        ".ts",
        ".webm",
        ".wmv",
    }
)


class MediaProcessingExecutionError(RuntimeError):
    pass


class MediaInspector(Protocol):
    async def inspect(self, path: Path) -> MediaProbe: ...


class MediaProcessingStateProtocol(Protocol):
    async def load(self, job_id: UUID) -> MediaProcessingContext: ...

    async def mark_processing(self, job_id: UUID) -> None: ...

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        media_path: str,
        probe: MediaProbe,
    ) -> None: ...

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None: ...


class MediaProcessingContext:
    def __init__(
        self,
        *,
        status: MediaProcessingJobStatus,
        download_directory: str,
        media_asset_ready: bool = False,
    ) -> None:
        self.status = status
        self.download_directory = download_directory
        self.media_asset_ready = media_asset_ready


class MediaProcessingState:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, job_id: UUID) -> MediaProcessingContext:
        async with self._session_factory() as session:
            job = await MediaProcessingJobService(session).get_job(job_id)
            asset = await MediaAssetService(session).get_for_episode(job.episode_id)
            return MediaProcessingContext(
                status=job.job_status,
                download_directory=job.download_directory,
                media_asset_ready=asset is not None and asset.metadata_ready,
            )

    async def mark_processing(self, job_id: UUID) -> None:
        async with self._session_factory() as session:
            await MediaProcessingJobService(session).mark_processing(job_id)

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        media_path: str,
        probe: MediaProbe,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            processing_service = MediaProcessingJobService(session)
            job = await processing_service.get_job(job_id)
            asset_metadata = _build_asset_metadata(probe)
            await MediaAssetService(session).upsert(
                episode_id=job.episode_id,
                processing_job_id=job.id,
                media_path=media_path,
                metadata=asset_metadata,
            )
            job.media_path = media_path
            job.probe_metadata = _serialize_probe(probe)
            job.transition_to(MediaProcessingJobStatus.COMPLETED)

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        async with self._session_factory() as session:
            await MediaProcessingJobService(session).mark_failed(
                job_id,
                error_message=error_message,
            )


class MediaProcessingRunner:
    def __init__(
        self,
        *,
        state: MediaProcessingStateProtocol,
        inspector: MediaInspector,
        download_root: Path,
    ) -> None:
        self._state = state
        self._inspector = inspector
        self._download_root = download_root

    async def run(self, job_id: UUID) -> None:
        job_loaded = False
        persist_failure = False
        try:
            context = await self._state.load(job_id)
            job_loaded = True
            persist_failure = context.status is not MediaProcessingJobStatus.COMPLETED
            if context.status is MediaProcessingJobStatus.COMPLETED and context.media_asset_ready:
                return

            if context.status is MediaProcessingJobStatus.FAILED:
                raise MediaProcessingExecutionError(
                    "Media processing job is failed and must be retried "
                    f"before execution: {job_id}",
                )

            if context.status is MediaProcessingJobStatus.PENDING:
                await self._state.mark_processing(job_id)

            media_path = _find_media_file(
                self._download_root / context.download_directory,
            )
            probe = await self._inspector.inspect(media_path)
            await self._state.mark_completed(
                job_id,
                media_path=str(media_path),
                probe=probe,
            )
        except Exception as exc:
            if job_loaded and persist_failure:
                try:
                    await self._state.mark_failed(
                        job_id,
                        error_message=_format_error(exc),
                    )
                except Exception:
                    logger.exception(
                        "Failed to persist media processing failure for job %s",
                        job_id,
                    )
            raise


def _find_media_file(root: Path) -> Path:
    if not root.is_dir():
        raise MediaProcessingExecutionError(
            f"Download directory does not exist: {root}",
        )

    candidates = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() in MEDIA_EXTENSIONS
    )
    if not candidates:
        raise MediaProcessingExecutionError(
            f"No supported media file found in download directory: {root}",
        )
    if len(candidates) > 1:
        names = ", ".join(str(path.relative_to(root)) for path in candidates[:5])
        suffix = " ..." if len(candidates) > 5 else ""
        raise MediaProcessingExecutionError(
            f"Expected exactly one media file in {root}, found {len(candidates)}: {names}{suffix}",
        )
    return candidates[0]


def _build_asset_metadata(probe: MediaProbe) -> MediaAssetMetadata:
    video_stream = _primary_stream(probe.video_streams)
    audio_stream = _primary_stream(probe.audio_streams)

    return MediaAssetMetadata(
        format_name=probe.format.format_name,
        duration_seconds=probe.format.duration_seconds,
        size_bytes=probe.format.size_bytes,
        video_codec=video_stream.codec_name if video_stream is not None else None,
        audio_codec=audio_stream.codec_name if audio_stream is not None else None,
        width=video_stream.width if video_stream is not None else None,
        height=video_stream.height if video_stream is not None else None,
        frame_rate=video_stream.frame_rate if video_stream is not None else None,
    )


def _primary_stream(streams: tuple[MediaStream, ...]) -> MediaStream | None:
    if not streams:
        return None

    return next(
        (stream for stream in streams if stream.disposition_default),
        streams[0],
    )


def _serialize_probe(probe: MediaProbe) -> dict[str, object]:
    payload = cast(dict[str, object], asdict(probe))
    payload.pop("path", None)
    return payload


def _format_error(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    return message[:2000]


def create_media_processing_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> MediaProcessingState:
    return MediaProcessingState(session_factory)
