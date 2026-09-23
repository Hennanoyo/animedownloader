from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Protocol, cast
from uuid import UUID

from animedownloader_media import MediaProbe
from animedownloader_media_processing import (
    MediaProcessingJobService,
    MediaProcessingJobStatus,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


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


class MediaProcessingContext:
    def __init__(
        self,
        *,
        status: MediaProcessingJobStatus,
        download_job_id: UUID,
    ) -> None:
        self.status = status
        self.download_job_id = download_job_id


class MediaProcessingState:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, job_id: UUID) -> MediaProcessingContext:
        async with self._session_factory() as session:
            job = await MediaProcessingJobService(session).get_job(job_id)
            if job.download_job_id is None:
                raise MediaProcessingExecutionError(
                    f"Download job provenance is missing: {job_id}",
                )
            return MediaProcessingContext(
                status=job.job_status,
                download_job_id=job.download_job_id,
            )

    async def mark_processing(self, job_id: UUID) -> None:
        async with self._session_factory() as session:
            await MediaProcessingJobService(session).mark_processing(job_id)

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        media_path: str,
        probe_metadata: dict[str, object],
    ) -> None:
        async with self._session_factory() as session:
            await MediaProcessingJobService(session).mark_completed(
                job_id,
                media_path=media_path,
                probe_metadata=probe_metadata,
            )

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
        state: MediaProcessingState,
        inspector: MediaInspector,
        download_root: Path,
    ) -> None:
        self._state = state
        self._inspector = inspector
        self._download_root = download_root

    async def run(self, job_id: UUID) -> None:
        try:
            context = await self._state.load(job_id)
            if context.status is MediaProcessingJobStatus.COMPLETED:
                return

            if context.status is MediaProcessingJobStatus.FAILED:
                raise MediaProcessingExecutionError(
                    f"Media processing job is failed and must be retried before execution: {job_id}",
                )

            if context.status is MediaProcessingJobStatus.PENDING:
                await self._state.mark_processing(job_id)

            media_path = _find_media_file(
                self._download_root / str(context.download_job_id),
            )
            probe = await self._inspector.inspect(media_path)
            await self._state.mark_completed(
                job_id,
                media_path=str(media_path),
                probe_metadata=_serialize_probe(probe),
            )
        except Exception as exc:
            await self._state.mark_failed(
                job_id,
                error_message=_format_error(exc),
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
