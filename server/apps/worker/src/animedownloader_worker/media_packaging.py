from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol
from uuid import UUID

from animedownloader_media import (
    CMAFPackagingResult,
    CMAFRepresentationMetadata,
    build_dash_manifest,
    build_hls_master_playlist,
    make_representation_metadata,
)
from animedownloader_media_asset import MediaAssetService
from animedownloader_media_processing import (
    MediaPackagingJobStatus,
    MediaStreamingPackageService,
)
from animedownloader_storage import Storage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class MediaPackagingExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaPackagingContext:
    job_id: UUID
    package_id: UUID
    variant_id: UUID
    source_path: str
    source_variant_updated_at: datetime
    status: MediaPackagingJobStatus
    width: int | None
    height: int | None
    size_bytes: int | None
    duration_seconds: float | None
    video_codec: str | None
    audio_codec: str | None
    source_is_current: bool = True


class MediaPackagingStateProtocol(Protocol):
    async def load(self, job_id: UUID) -> MediaPackagingContext: ...

    async def mark_processing(self, job_id: UUID) -> None: ...

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        representation: CMAFRepresentationMetadata,
        package_root_key: str,
    ) -> None: ...

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None: ...


class MediaPackagingState:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, job_id: UUID) -> MediaPackagingContext:
        async with self._session_factory() as session:
            service = MediaStreamingPackageService(session)
            job = await service.get_job(job_id)
            variant = await service.get_variant(job.media_variant_id)
            if variant is None:
                raise MediaPackagingExecutionError(
                    f"Playable media variant does not exist: {job.media_variant_id}",
                )

            asset = await MediaAssetService(session).get(variant.media_asset_id)
            if asset is None:
                raise MediaPackagingExecutionError(
                    f"Media asset does not exist: {variant.media_asset_id}",
                )

            variant_source_current = (
                variant.ready
                and variant.path == job.source_path
                and variant.updated_at == job.source_variant_updated_at
            )
            source_is_current = (
                asset.path == variant.source_path
                and asset.metadata_updated_at == variant.source_metadata_updated_at
                and variant_source_current
            )

            return MediaPackagingContext(
                job_id=job.id,
                package_id=job.package_id,
                variant_id=variant.id,
                source_path=job.source_path,
                source_variant_updated_at=job.source_variant_updated_at,
                status=job.job_status,
                width=variant.width,
                height=variant.height,
                size_bytes=variant.size_bytes,
                duration_seconds=variant.duration_seconds,
                video_codec=variant.video_codec,
                audio_codec=variant.audio_codec,
                source_is_current=source_is_current,
            )

    async def mark_processing(self, job_id: UUID) -> None:
        async with self._session_factory() as session:
            await MediaStreamingPackageService(session).mark_processing(job_id)

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        representation: CMAFRepresentationMetadata,
        package_root_key: str,
    ) -> None:
        async with self._session_factory() as session:
            await MediaStreamingPackageService(session).mark_completed(
                job_id,
                hls_master_key=f"{package_root_key}/master.m3u8",
                dash_manifest_key=f"{package_root_key}/manifest.mpd",
                quality=representation.quality,
                width=representation.width,
                height=representation.height,
                bandwidth=representation.bandwidth,
                video_codec=representation.video_codec,
                audio_codec=representation.audio_codec,
                duration_seconds=representation.duration_seconds,
                hls_playlist_key=(
                    f"{package_root_key}/{representation.quality}/index.m3u8"
                ),
                init_segment_key=(
                    f"{package_root_key}/{representation.quality}/init.mp4"
                ),
                segment_directory_key=(
                    f"{package_root_key}/{representation.quality}/s"
                ),
            )

    async def mark_failed(self, job_id: UUID, *, error_message: str) -> None:
        async with self._session_factory() as session:
            await MediaStreamingPackageService(session).mark_failed(
                job_id,
                error_message=error_message,
            )


class CMAFPackagingProcessor(Protocol):
    async def process(
        self,
        *,
        media_path: Path,
        output_dir: Path,
    ) -> CMAFPackagingResult: ...


class MediaPackagingRunner:
    def __init__(
        self,
        *,
        state: MediaPackagingStateProtocol,
        processor: CMAFPackagingProcessor,
        storage: Storage,
    ) -> None:
        self._state = state
        self._processor = processor
        self._storage = storage

    async def run(self, job_id: UUID) -> None:
        context: MediaPackagingContext | None = None
        try:
            context = await self._state.load(job_id)
            if context.status is MediaPackagingJobStatus.COMPLETED:
                return
            if not context.source_is_current:
                raise MediaPackagingExecutionError(
                    "Playable media variant changed after the packaging job was created; "
                    "create a new packaging job",
                )
            if context.width is None or context.height is None:
                raise MediaPackagingExecutionError(
                    "Playable media variant is missing video dimensions",
                )

            if context.status is MediaPackagingJobStatus.PENDING:
                await self._state.mark_processing(job_id)
            elif context.status is not MediaPackagingJobStatus.PROCESSING:
                raise MediaPackagingExecutionError(
                    "Packaging job cannot be executed from status "
                    f"{context.status.value}",
                )

            quality = f"{context.height}p"
            package_root_key = f"streaming/{context.variant_id}"

            with TemporaryDirectory(prefix="animedownloader-packaging-") as staging_dir:
                staging_root = Path(staging_dir)
                source_path = staging_root / "source.mp4"
                package_root = staging_root / "streaming" / str(context.variant_id)
                representation_dir = package_root / quality

                await self._storage.materialize(
                    context.source_path,
                    source_path,
                )
                packaged = await self._processor.process(
                    media_path=source_path,
                    output_dir=representation_dir,
                )
                representation = make_representation_metadata(
                    quality=quality,
                    width=context.width,
                    height=context.height,
                    size_bytes=context.size_bytes,
                    duration_seconds=context.duration_seconds,
                    video_codec=context.video_codec,
                    audio_codec=context.audio_codec,
                    segments=packaged.segments,
                )
                package_root.mkdir(parents=True, exist_ok=True)
                (package_root / "master.m3u8").write_text(
                    build_hls_master_playlist((representation,)),
                    encoding="utf-8",
                )
                (package_root / "manifest.mpd").write_text(
                    build_dash_manifest(
                        (representation,),
                        media_presentation_duration_seconds=representation.duration_seconds,
                    ),
                    encoding="utf-8",
                )

                await _upload_tree(
                    self._storage,
                    package_root,
                    package_root_key,
                )

            await self._state.mark_completed(
                job_id,
                representation=representation,
                package_root_key=package_root_key,
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
                        "Failed to persist media packaging failure for job %s",
                        job_id,
                    )
            raise



async def _upload_tree(
    storage: Storage,
    root: Path,
    object_prefix: str,
) -> None:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        content_type = mimetypes.guess_type(path.name)[0]
        await storage.put_file(
            path,
            f"{object_prefix}/{relative}",
            content_type=content_type,
        )


def _format_error(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    return message[:2000]


def create_media_packaging_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> MediaPackagingState:
    return MediaPackagingState(session_factory)
