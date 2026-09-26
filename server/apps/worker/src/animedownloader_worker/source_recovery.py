from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from uuid import UUID

from animedownloader_database import Database
from animedownloader_download import DownloadJob, DownloadJobStatus
from animedownloader_media_processing import MediaProcessingJobService, MediaProcessingJobStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .media_source import MediaSourceStatus, resolve_media_source

logger = logging.getLogger(__name__)

MediaProcessingEnqueuer = Callable[[UUID], Awaitable[None]]


async def recover_completed_download_handoffs(
    database: Database,
    *,
    download_root: Path,
    enqueue_media_processing: MediaProcessingEnqueuer,
) -> tuple[int, int]:
    async with database.session_factory() as session:
        completed_ids = await _completed_downloads_without_processing_jobs(session)

    recovered = 0
    unresolved = 0

    for download_job_id in completed_ids:
        resolution = resolve_media_source(download_root / str(download_job_id))
        if resolution.status is not MediaSourceStatus.FOUND:
            unresolved += 1
            logger.warning(
                "completed download has unresolved media source: "
                "download_job_id=%s status=%s root=%s",
                download_job_id,
                resolution.status.value,
                resolution.root,
            )
            continue

        async with database.session_factory() as session:
            job, created = await MediaProcessingJobService(
                session,
            ).ensure_for_download_job(download_job_id)

        if not created:
            if job.job_status in {
                MediaProcessingJobStatus.PENDING,
                MediaProcessingJobStatus.PROCESSING,
            }:
                logger.info(
                    "completed download already has active media handoff: "
                    "download_job_id=%s media_job_id=%s status=%s",
                    download_job_id,
                    job.id,
                    job.status,
                )
            continue

        await enqueue_media_processing(job.id)
        recovered += 1
        logger.info(
            "recovered completed download handoff: "
            "download_job_id=%s media_job_id=%s source=%s",
            download_job_id,
            job.id,
            resolution.path,
        )

    return recovered, unresolved


async def _completed_downloads_without_processing_jobs(
    session: AsyncSession,
) -> list[UUID]:
    result = await session.scalars(
        select(DownloadJob.id)
        .outerjoin(
            __import__(
                "animedownloader_media_processing",
                fromlist=["MediaProcessingJob"],
            ).MediaProcessingJob,
            __import__(
                "animedownloader_media_processing",
                fromlist=["MediaProcessingJob"],
            ).MediaProcessingJob.download_job_id == DownloadJob.id,
        )
        .where(
            DownloadJob.status == DownloadJobStatus.COMPLETED.value,
        )
        .where(
            __import__(
                "animedownloader_media_processing",
                fromlist=["MediaProcessingJob"],
            ).MediaProcessingJob.id.is_(None),
        )
        .order_by(DownloadJob.completed_at.asc(), DownloadJob.id.asc()),
    )
    return list(result)
