from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from animedownloader_media import (
    FFmpegPlayableMediaProcessor,
    FFprobeInspector,
    MediaProbe,
    PlayableMediaOperation,
    PlayableMediaPlanner,
)
from animedownloader_media_processing import (
    MediaTranscodingJob,
    MediaTranscodingJobService,
    MediaTranscodingJobStatus,
    MediaVariant,
    MediaVariantService,
)
from animedownloader_media_asset import MediaAssetService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class MediaTranscodingExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaTranscodingContext:
    job_id: UUID
    asset_id: UUID
    source_path: str
    source_metadata_updated_at: datetime
    status: MediaTranscodingJobStatus
    operation: PlayableMediaOperation | None
    variant_id: UUID


class MediaTranscodingStateProtocol:
    async def load(self, job_id: UUID) -> MediaTranscodingContext: ...

    async def mark_processing(
        self,
        job_id: UUID,
        operation: PlayableMediaOperation,
    ) -> None: ...

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        output_path: Path,
        probe: MediaProbe,
    ) -> None: ...

    async def mark_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
    ) -> None: ...


class MediaTranscodingState:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, job_id: UUID) -> MediaTranscodingContext:
        async with self._session_factory() as session:
            job = await MediaTranscodingJobService(session).get_job(job_id)
            asset = await MediaAssetService(session).get(job.media_asset_id)
            if asset is None:
                raise MediaTranscodingExecutionError(
                    f"Media asset does not exist: {job.media_asset_id}",
                )
            if not asset.metadata_ready or asset.metadata_updated_at is None:
                raise MediaTranscodingExecutionError(
                    f"Media asset metadata is not ready: {asset.id}",
                )

            variant = await MediaVariantService(session).get(job.variant_id)
            if variant is None:
                raise MediaTranscodingExecutionError(
                    f"Media variant does not exist: {job.variant_id}",
                )

            return MediaTranscodingContext(
                job_id=job.id,
                asset_id=asset.id,
                source_path=asset.path,
                source_metadata_updated_at=asset.metadata_updated_at,
                status=job.job_status,
                operation=job.transcoding_operation,
                variant_id=variant.id,
            )

    async def mark_processing(
        self,
        job_id: UUID,
        operation: PlayableMediaOperation,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            job_service = MediaTranscodingJobService(session)
            variant_service = MediaVariantService(session)
            job = await job_service.get_job(job_id)
            variant = await variant_service.get(job.variant_id)
            if variant is None:
                raise MediaTranscodingExecutionError(
                    f"Media variant does not exist: {job.variant_id}",
                )

            job.transition_to(MediaTranscodingJobStatus.PROCESSING)
            job.operation = operation.value
            variant.mark_processing()

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        output_path: Path,
        probe: MediaProbe,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            job_service = MediaTranscodingJobService(session)
            variant_service = MediaVariantService(session)
            job = await job_service.get_job(job_id)
            variant = await variant_service.get(job.variant_id)
            if variant is None:
                raise MediaTranscodingExecutionError(
                    f"Media variant does not exist: {job.variant_id}",
                )

            variant.mark_completed(
                source_path=job.source_path,
                source_metadata_updated_at=job.source_metadata_updated_at,
                output_path=str(output_path),
                probe=probe,
            )
            job.output_path = str(output_path)
            job.transition_to(MediaTranscodingJobStatus.COMPLETED)

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        async with self._session_factory() as session, session.begin():
            job_service = MediaTranscodingJobService(session)
            variant_service = MediaVariantService(session)
            job = await job_service.get_job(job_id)
            variant = await variant_service.get(job.variant_id)
            if variant is None:
                raise MediaTranscodingExecutionError(
                    f"Media variant does not exist: {job.variant_id}",
                )

            job.transition_to(MediaTranscodingJobStatus.FAILED)
            job.error_message = error_message[:2000]
            variant.mark_failed(error_message)


class MediaTranscodingRunner:
    def __init__(
        self,
        *,
        state: MediaTranscodingStateProtocol,
        inspector: FFprobeInspector,
        planner: PlayableMediaPlanner,
        processor: FFmpegPlayableMediaProcessor,
        media_root: Path,
    ) -> None:
        self._state = state
        self._inspector = inspector
        self._planner = planner
        self._processor = processor
        self._media_root = media_root

    async def run(self, job_id: UUID) -> None:
        context: MediaTranscodingContext | None = None
        try:
            context = await self._state.load(job_id)
            if context.status is MediaTranscodingJobStatus.COMPLETED:
                return

            source_path = Path(context.source_path)
            probe = await self._inspector.inspect(source_path)
            operation = self._planner.plan(probe)

            if context.status is MediaTranscodingJobStatus.PENDING:
                await self._state.mark_processing(job_id, operation)
            elif context.status is MediaTranscodingJobStatus.PROCESSING:
                if context.operation is not None and context.operation is not operation:
                    raise MediaTranscodingExecutionError(
                        "Transcoding operation changed while a job was processing: "
                        f"{context.operation.value} -> {operation.value}",
                    )
            else:
                raise MediaTranscodingExecutionError(
                    f"Transcoding job cannot be executed from status {context.status.value}",
                )

            output_dir = self._media_root / "playable" / str(context.asset_id)
            output_path = output_dir / f"{job_id}.mp4"
            result = await self._processor.process(
                media_path=source_path,
                output_path=output_path,
                operation=operation,
            )
            output_probe = await self._inspector.inspect(result.output_path)
            self._planner.validate(output_probe)

            await self._state.mark_completed(
                job_id,
                output_path=result.output_path,
                probe=output_probe,
            )
        except Exception as exc:
            if context is not None:
                try:
                    await self._state.mark_failed(
                        job_id,
                        error_message=_format_error(exc),
                    )
                except Exception:
                    logger.exception(
                        "Failed to persist media transcoding failure for job %s",
                        job_id,
                    )
            raise


def _format_error(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    return message[:2000]


def create_media_transcoding_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> MediaTranscodingState:
    return MediaTranscodingState(session_factory)
