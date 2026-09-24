from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol
from uuid import UUID

from animedownloader_media import (
    MediaPreparationProcessingResult,
    MediaProbe,
    PlayableMediaOperation,
    PlayableMediaPlanner,
    PlayableMediaProcessingResult,
    ThumbnailSpriteResult,
)
from animedownloader_media_asset import MediaAssetService
from animedownloader_media_processing import (
    MediaPreparationJobService,
    MediaPreparationJobStatus,
    MediaTranscodingOperation,
    MediaVariantService,
)
from animedownloader_storage import PlayableArtifact, Storage, ThumbnailArtifact
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class MediaPreparationExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaPreparationContext:
    job_id: UUID
    asset_id: UUID
    source_path: str
    source_metadata_updated_at: datetime
    status: MediaPreparationJobStatus
    operation: MediaTranscodingOperation | None
    variant_id: UUID
    playable_ready: bool
    thumbnail_ready: bool
    duration_seconds: float | None
    source_is_current: bool = True


class MediaPreparationStateProtocol(Protocol):
    async def load(self, job_id: UUID) -> MediaPreparationContext: ...

    async def mark_processing(
        self,
        job_id: UUID,
        *,
        operation: MediaTranscodingOperation | None,
        playable_required: bool,
        thumbnail_required: bool,
    ) -> None: ...

    async def update_operation(
        self,
        job_id: UUID,
        *,
        operation: MediaTranscodingOperation | None,
    ) -> None: ...

    async def update_operation(
        self,
        job_id: UUID,
        *,
        operation: MediaTranscodingOperation | None,
    ) -> None:
        async with self._session_factory() as session:
            await MediaPreparationJobService(session).update_operation(
                job_id,
                operation=operation,
            )

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        playable_probe: MediaProbe | None,
        playable_output_key: str | None,
        thumbnail: ThumbnailSpriteResult | None,
        thumbnail_sprite_key: str | None,
        thumbnail_vtt_key: str | None,
    ) -> None: ...

    async def mark_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
    ) -> None: ...


class MediaPreparationState:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, job_id: UUID) -> MediaPreparationContext:
        async with self._session_factory() as session:
            job = await MediaPreparationJobService(session).get_job(job_id)
            asset = await MediaAssetService(session).get(job.media_asset_id)
            if asset is None:
                raise MediaPreparationExecutionError(
                    f"Media asset does not exist: {job.media_asset_id}",
                )
            if not asset.metadata_ready or asset.metadata_updated_at is None:
                raise MediaPreparationExecutionError(
                    f"Media asset metadata is not ready: {asset.id}",
                )

            variant = await MediaVariantService(session).get(job.variant_id)
            if variant is None:
                raise MediaPreparationExecutionError(
                    f"Media variant does not exist: {job.variant_id}",
                )

            return MediaPreparationContext(
                job_id=job.id,
                asset_id=asset.id,
                source_path=job.source_path,
                source_metadata_updated_at=job.source_metadata_updated_at,
                status=job.job_status,
                operation=job.transcoding_operation,
                variant_id=variant.id,
                playable_ready=variant.is_current(
                    source_path=job.source_path,
                    source_metadata_updated_at=job.source_metadata_updated_at,
                ),
                thumbnail_ready=asset.thumbnail_ready,
                duration_seconds=asset.duration_seconds,
                source_is_current=(
                    asset.path == job.source_path
                    and asset.metadata_updated_at == job.source_metadata_updated_at
                ),
            )

    async def mark_processing(
        self,
        job_id: UUID,
        *,
        operation: MediaTranscodingOperation | None,
        playable_required: bool,
        thumbnail_required: bool,
    ) -> None:
        async with self._session_factory() as session:
            await MediaPreparationJobService(session).mark_processing(
                job_id,
                operation=operation,
                playable_required=playable_required,
                thumbnail_required=thumbnail_required,
            )

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        playable_probe: MediaProbe | None,
        playable_output_key: str | None,
        thumbnail: ThumbnailSpriteResult | None,
        thumbnail_sprite_key: str | None,
        thumbnail_vtt_key: str | None,
    ) -> None:
        async with self._session_factory() as session:
            service = MediaPreparationJobService(session)
            video_stream = (
                next(iter(playable_probe.video_streams), None)
                if playable_probe is not None
                else None
            )
            audio_stream = (
                next(iter(playable_probe.audio_streams), None)
                if playable_probe is not None
                else None
            )
            await service.mark_completed(
                job_id,
                playable_output_path=playable_output_key,
                format_name=(
                    playable_probe.format.format_name if playable_probe is not None else None
                ),
                duration_seconds=(
                    playable_probe.format.duration_seconds if playable_probe is not None else None
                ),
                size_bytes=(
                    playable_probe.format.size_bytes if playable_probe is not None else None
                ),
                video_codec=video_stream.codec_name if video_stream is not None else None,
                audio_codec=audio_stream.codec_name if audio_stream is not None else None,
                width=video_stream.width if video_stream is not None else None,
                height=video_stream.height if video_stream is not None else None,
                frame_rate=video_stream.frame_rate if video_stream is not None else None,
                thumbnail_sprite_path=thumbnail_sprite_key,
                thumbnail_vtt_path=thumbnail_vtt_key,
            )

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        async with self._session_factory() as session:
            await MediaPreparationJobService(session).mark_failed(
                job_id,
                error_message=error_message,
            )


class MediaInspector(Protocol):
    async def inspect(self, path: Path) -> MediaProbe: ...


class MediaPreparationProcessor(Protocol):
    async def process(
        self,
        *,
        media_path: Path,
        playable_path: Path,
        sprite_path: Path,
        vtt_path: Path,
        duration_seconds: float | None,
        operation: PlayableMediaOperation,
    ) -> MediaPreparationProcessingResult: ...


class PlayableMediaProcessor(Protocol):
    async def process(
        self,
        *,
        media_path: Path,
        output_path: Path,
        operation: PlayableMediaOperation,
    ) -> PlayableMediaProcessingResult: ...


class ThumbnailProcessor(Protocol):
    async def generate(
        self,
        *,
        media_path: Path,
        output_dir: Path,
        duration_seconds: float | None,
    ) -> ThumbnailSpriteResult: ...


class MediaPreparationRunner:
    def __init__(
        self,
        *,
        state: MediaPreparationStateProtocol,
        inspector: MediaInspector,
        planner: PlayableMediaPlanner,
        preparation_processor: MediaPreparationProcessor,
        playable_processor: PlayableMediaProcessor,
        thumbnail_processor: ThumbnailProcessor,
        storage: Storage,
    ) -> None:
        self._state = state
        self._inspector = inspector
        self._planner = planner
        self._preparation_processor = preparation_processor
        self._playable_processor = playable_processor
        self._thumbnail_processor = thumbnail_processor
        self._storage = storage

    async def run(self, job_id: UUID) -> None:
        context: MediaPreparationContext | None = None
        try:
            context = await self._state.load(job_id)
            print(
                "[worker] media preparation loaded: "
                f"job_id={job_id} asset_id={context.asset_id} "
                f"status={context.status.value} "
                f"operation={context.operation.value if context.operation is not None else None} "
                f"playable_ready={context.playable_ready} "
                f"thumbnail_ready={context.thumbnail_ready}",
                flush=True,
            )
            if context.status is MediaPreparationJobStatus.COMPLETED:
                return
            if context.status is MediaPreparationJobStatus.FAILED:
                print(
                    "[worker] media preparation task ignored for failed job: "
                    f"job_id={job_id}",
                    flush=True,
                )
                return
            if not context.source_is_current:
                raise MediaPreparationExecutionError(
                    "Media asset source changed after the preparation job was created; "
                    "create a new preparation job",
                )

            playable_required = not context.playable_ready
            thumbnail_required = not context.thumbnail_ready
            if not playable_required and not thumbnail_required:
                print(
                    f"[worker] media preparation already complete: job_id={job_id}",
                    flush=True,
                )
                await self._state.mark_completed(
                    job_id,
                    playable_probe=None,
                    playable_output_key=None,
                    thumbnail=None,
                    thumbnail_sprite_key=None,
                    thumbnail_vtt_key=None,
                )
                return

            source_probe: MediaProbe | None = None
            operation: PlayableMediaOperation | None = None
            if playable_required:
                source_probe = await self._inspector.inspect(Path(context.source_path))
                operation = self._planner.plan(source_probe)

            if context.status is MediaPreparationJobStatus.PENDING:
                print(
                    "[worker] media preparation entering processing: "
                    f"job_id={job_id} "
                    f"operation={operation.value if operation is not None else None} "
                    f"playable_required={playable_required} "
                    f"thumbnail_required={thumbnail_required}",
                    flush=True,
                )
                await self._state.mark_processing(
                    job_id,
                    operation=(
                        MediaTranscodingOperation(operation.value)
                        if operation is not None
                        else None
                    ),
                    playable_required=playable_required,
                    thumbnail_required=thumbnail_required,
                )
            elif context.status is MediaPreparationJobStatus.PROCESSING:
                if (
                    operation is not None
                    and context.operation is not None
                    and context.operation.value != operation.value
                ):
                    print(
                        "[worker] media preparation operation changed while resuming: "
                        f"job_id={job_id} "
                        f"{context.operation.value} -> {operation.value}",
                        flush=True,
                    )
                    await self._state.update_operation(
                        job_id,
                        operation=MediaTranscodingOperation(operation.value),
                    )
            else:
                raise MediaPreparationExecutionError(
                    f"Preparation job cannot be executed from status {context.status.value}",
                )

            playable_probe: MediaProbe | None = None
            playable_output_path: Path | None = None
            thumbnail: ThumbnailSpriteResult | None = None
            playable_output_key: str | None = None
            thumbnail_sprite_key: str | None = None
            thumbnail_vtt_key: str | None = None

            with TemporaryDirectory(prefix="animedownloader-preparation-") as staging_dir:
                staging_root = Path(staging_dir)
                output_dir = staging_root / "playable" / str(context.asset_id)
                playable_path = output_dir / f"{job_id}.mp4"
                thumbnail_dir = staging_root / "thumbnails" / str(context.asset_id)
                sprite_path = thumbnail_dir / "sprite.jpg"
                vtt_path = thumbnail_dir / "sprite.vtt"

                if playable_required and thumbnail_required:
                    if operation is None or source_probe is None:
                        raise MediaPreparationExecutionError(
                            "A playable operation is required for combined preparation",
                        )
                    print(
                        "[worker] media preparation FFmpeg started: "
                        f"job_id={job_id} mode=staged operation={operation.value}",
                        flush=True,
                    )
                    combined = await self._preparation_processor.process(
                        media_path=Path(context.source_path),
                        playable_path=playable_path,
                        sprite_path=sprite_path,
                        vtt_path=vtt_path,
                        duration_seconds=source_probe.format.duration_seconds,
                        operation=operation,
                    )
                    playable_output_path = combined.playable.output_path
                    playable_probe = await self._inspector.inspect(playable_output_path)
                    self._planner.validate(playable_probe)
                    thumbnail = combined.thumbnail
                elif playable_required:
                    if operation is None:
                        raise MediaPreparationExecutionError(
                            "A playable operation is required for playable preparation",
                        )
                    print(
                        "[worker] media preparation FFmpeg started: "
                        f"job_id={job_id} mode=playable operation={operation.value}",
                        flush=True,
                    )
                    result = await self._playable_processor.process(
                        media_path=Path(context.source_path),
                        output_path=playable_path,
                        operation=operation,
                    )
                    playable_output_path = result.output_path
                    playable_probe = await self._inspector.inspect(playable_output_path)
                    self._planner.validate(playable_probe)
                else:
                    print(
                        "[worker] media preparation FFmpeg started: "
                        f"job_id={job_id} mode=thumbnail",
                        flush=True,
                    )
                    thumbnail = await self._thumbnail_processor.generate(
                        media_path=Path(context.source_path),
                        output_dir=thumbnail_dir,
                        duration_seconds=context.duration_seconds,
                    )

                if playable_output_path is not None:
                    playable_output_key = PlayableArtifact(
                        asset_id=context.asset_id,
                        variant_id=context.variant_id,
                    ).object_key
                    print(
                        "[worker] media preparation uploading playable: "
                        f"job_id={job_id} key={playable_output_key}",
                        flush=True,
                    )
                    await self._storage.put_file(
                        playable_output_path,
                        playable_output_key,
                        content_type="video/mp4",
                    )

                if thumbnail is not None:
                    thumbnail_sprite_key = ThumbnailArtifact(
                        asset_id=context.asset_id,
                        kind="sprite",
                    ).object_key
                    thumbnail_vtt_key = ThumbnailArtifact(
                        asset_id=context.asset_id,
                        kind="vtt",
                    ).object_key
                    await self._storage.put_file(
                        thumbnail.sprite_path,
                        thumbnail_sprite_key,
                        content_type="image/jpeg",
                    )
                    await self._storage.put_file(
                        thumbnail.vtt_path,
                        thumbnail_vtt_key,
                        content_type="text/vtt",
                    )

            print(
                "[worker] media preparation completed: "
                f"job_id={job_id} playable_key={playable_output_key} "
                f"thumbnail={thumbnail is not None}",
                flush=True,
            )
            await self._state.mark_completed(
                job_id,
                playable_probe=playable_probe,
                playable_output_key=playable_output_key,
                thumbnail=thumbnail,
                thumbnail_sprite_key=thumbnail_sprite_key,
                thumbnail_vtt_key=thumbnail_vtt_key,
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
                        "Failed to persist media preparation failure for job %s",
                        job_id,
                    )
            raise


def _format_error(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    return message[:2000]


def create_media_preparation_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> MediaPreparationState:
    return MediaPreparationState(session_factory)
