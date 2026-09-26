from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from animedownloader_anime import AnimeService
from animedownloader_download import (
    DownloadJob,
    DownloadJobService,
    DownloadJobStatus,
    find_download_directories,
    relative_media_source,
    resolve_media_source,
    resolve_selected_media_source,
)
from animedownloader_media_processing import (
    MediaProcessingJob,
    MediaProcessingJobService,
    MediaProcessingJobStatus,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .media_processing_queue import MediaProcessingTaskDispatcher
from .task_queue import DownloadTaskDispatcher


class MediaSourceRecoveryError(RuntimeError):
    pass


class MediaSourceRecoveryConflictError(MediaSourceRecoveryError):
    pass


@dataclass(frozen=True, slots=True)
class MediaSourceCandidate:
    path: str


@dataclass(frozen=True, slots=True)
class EpisodeMediaSource:
    episode_id: UUID
    download_job_id: UUID | None
    download_status: DownloadJobStatus | None
    status: str
    root: str | None
    selected_path: str | None
    candidates: tuple[MediaSourceCandidate, ...]
    processing_job_id: UUID | None
    processing_status: MediaProcessingJobStatus | None


@dataclass(frozen=True, slots=True)
class MediaSourceOrphan:
    directory_id: UUID
    path: str


class MediaSourceService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        download_root: Path,
        download_dispatcher: DownloadTaskDispatcher,
        media_dispatcher: MediaProcessingTaskDispatcher,
    ) -> None:
        self._session = session
        self._download_root = download_root
        self._anime = AnimeService(session)
        self._downloads = DownloadJobService(session)
        self._processing = MediaProcessingJobService(session)
        self._download_dispatcher = download_dispatcher
        self._media_dispatcher = media_dispatcher

    async def get_episode_source(self, episode_id: UUID) -> EpisodeMediaSource:
        await self._anime.get_episode(episode_id)
        download = await self._downloads.get_latest_completed_job(episode_id)
        if download is None:
            return EpisodeMediaSource(
                episode_id=episode_id,
                download_job_id=None,
                download_status=None,
                status="not_available",
                root=None,
                selected_path=None,
                candidates=(),
                processing_job_id=None,
                processing_status=None,
            )

        root = self._download_root / str(download.id)
        resolution = resolve_media_source(root)
        processing = await self._processing.get_latest_job(episode_id)

        selected_path = None
        if processing is not None and processing.download_job_id == download.id:
            if processing.media_path is not None:
                selected = resolve_selected_media_source(root, _relative_source_path(root, processing.media_path))
                if selected is not None:
                    selected_path = relative_media_source(root, selected)

        return EpisodeMediaSource(
            episode_id=episode_id,
            download_job_id=download.id,
            download_status=download.job_status,
            status=resolution.status.value,
            root=str(root),
            selected_path=selected_path,
            candidates=tuple(
                MediaSourceCandidate(path=relative_media_source(root, path))
                for path in resolution.candidates
            ),
            processing_job_id=(
                processing.id
                if processing is not None and processing.download_job_id == download.id
                else None
            ),
            processing_status=(
                processing.job_status
                if processing is not None and processing.download_job_id == download.id
                else None
            ),
        )

    async def reprocess(self, episode_id: UUID) -> MediaProcessingJob:
        download = await self._require_completed_download(episode_id)
        resolution = resolve_media_source(self._download_root / str(download.id))
        if not resolution.is_ready:
            raise MediaSourceRecoveryConflictError(
                "Media source is not ready for processing.",
            )

        processing, _created = await self._processing.ensure_for_download_job(download.id)
        if processing.job_status is MediaProcessingJobStatus.PROCESSING:
            raise MediaSourceRecoveryConflictError(
                "Media processing is already in progress.",
            )
        if processing.job_status is MediaProcessingJobStatus.COMPLETED:
            raise MediaSourceRecoveryConflictError(
                "Media processing is already complete for this source.",
            )
        if processing.job_status is MediaProcessingJobStatus.FAILED:
            processing = await self._processing.retry_job(processing.id)

        await self._enqueue_processing(processing.id)
        return processing

    async def redownload(self, episode_id: UUID) -> DownloadJob:
        await self._anime.get_episode(episode_id)
        job = await self._downloads.create_job(episode_id)
        await self._enqueue_download(job.id)
        return job

    async def select_source(
        self,
        episode_id: UUID,
        relative_path: str,
    ) -> MediaProcessingJob:
        download = await self._require_completed_download(episode_id)
        root = self._download_root / str(download.id)
        selected_path = resolve_selected_media_source(root, relative_path)
        if selected_path is None:
            raise MediaSourceRecoveryConflictError(
                "Selected media source is missing, unsupported, or outside the download directory.",
            )

        processing, _created = await self._processing.ensure_for_download_job(download.id)
        if processing.job_status is MediaProcessingJobStatus.PROCESSING:
            raise MediaSourceRecoveryConflictError(
                "Media processing is already in progress.",
            )
        if processing.job_status is MediaProcessingJobStatus.COMPLETED:
            raise MediaSourceRecoveryConflictError(
                "Completed media processing cannot change its source.",
            )

        processing = await self._processing.select_source(
            processing.id,
            media_path=relative_media_source(root, selected_path),
        )
        await self._enqueue_processing(processing.id)
        return processing

    async def list_orphans(self) -> list[MediaSourceOrphan]:
        async with self._session.begin():
            result = await self._session.scalars(select(DownloadJob.id))
            known_ids = set(result)

        return [
            MediaSourceOrphan(
                directory_id=UUID(directory.name),
                path=str(directory),
            )
            for directory in find_download_directories(self._download_root)
            if UUID(directory.name) not in known_ids
        ]

    async def delete_orphan(self, directory_id: UUID) -> None:
        async with self._session.begin():
            exists = await self._session.scalar(
                select(DownloadJob.id).where(DownloadJob.id == directory_id),
            )

        if exists is not None:
            raise MediaSourceRecoveryConflictError(
                "Download directory belongs to a persisted download job.",
            )

        directory = self._download_root / str(directory_id)
        if not directory.is_dir():
            raise FileNotFoundError(directory)

        if directory.resolve().parent != self._download_root.resolve():
            raise MediaSourceRecoveryConflictError(
                "Refusing to delete a directory outside the configured download root.",
            )

        shutil.rmtree(directory)

    async def _require_completed_download(self, episode_id: UUID) -> DownloadJob:
        await self._anime.get_episode(episode_id)
        download = await self._downloads.get_latest_completed_job(episode_id)
        if download is None:
            raise MediaSourceRecoveryConflictError(
                "No completed download is available for this episode.",
            )
        return download

    async def _enqueue_processing(self, job_id: UUID) -> None:
        try:
            await self._media_dispatcher.enqueue(job_id)
        except Exception as exc:
            raise MediaSourceRecoveryError(
                "Media processing task queue is temporarily unavailable",
            ) from exc

    async def _enqueue_download(self, job_id: UUID) -> None:
        try:
            await self._download_dispatcher.enqueue(job_id)
        except Exception as exc:
            await self._downloads.mark_failed(
                job_id,
                error_message="Failed to enqueue download task.",
            )
            raise MediaSourceRecoveryError(
                "Download task queue is temporarily unavailable",
            ) from exc


def _relative_source_path(root: Path, path: str) -> str:
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path
