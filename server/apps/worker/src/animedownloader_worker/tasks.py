from uuid import UUID

from animedownloader_anime import Anime
from animedownloader_api.release_candidates import ReleaseDiscoveryCandidateService
from animedownloader_api.release_discovery import ReleaseDiscoveryService
from animedownloader_api.task_queue import RELEASE_DISCOVERY_TASK_NAME
from animedownloader_config import Settings
from animedownloader_database import Database, create_database
from animedownloader_download import DOWNLOAD_TASK_NAME, DownloadJobService
from animedownloader_media import (
    FFmpegAttachmentProcessor,
    FFmpegCMAFProcessor,
    FFmpegMediaPreparationProcessor,
    FFmpegPlayableMediaProcessor,
    FFmpegSubtitleProcessor,
    FFmpegThumbnailSpriteProcessor,
    FFprobeInspector,
    PlayableMediaPlanner,
    SubprocessFFmpegRunner,
    resolve_video_encoder,
)
from animedownloader_media_asset import (
    MEDIA_ATTACHMENT_PROCESSING_TASK_NAME,
    SUBTITLE_PROCESSING_TASK_NAME,
    MediaAssetService,
)
from animedownloader_media_processing import (

    MEDIA_PACKAGING_TASK_NAME,
    MEDIA_PREPARATION_TASK_NAME,
    MEDIA_PROCESSING_TASK_NAME,
    MediaPreparationJobService,
    MediaProcessingJobService,
    MediaProcessingJobStatus,
    MediaStreamingPackageService,
    MediaVariantService,
)
from animedownloader_nyaa import NyaaClient
from animedownloader_qbittorrent import QBittorrentClient
from animedownloader_releases import SearchField
from sqlalchemy import select

from .broker import broker
from .media_attachment_processing import (
    MediaAttachmentProcessingRunner,
    create_media_attachment_processing_state,
)
from .media_packaging import MediaPackagingRunner, create_media_packaging_state
from .media_preparation import MediaPreparationRunner, create_media_preparation_state
from .media_processing import MediaProcessingRunner, create_media_processing_state
from .progress import RedisJobProgressPublisher
from .runner import DownloadRunner, create_download_state
from .storage import create_media_storage
from .subtitle_processing import (
    SubtitleProcessingRunner,
    create_subtitle_processing_state,
)

print("[worker] task module loaded", flush=True)


@broker.task(task_name=RELEASE_DISCOVERY_TASK_NAME)
async def run_release_discovery(run_id: str) -> None:
    print(f"[worker] release discovery started: run_id={run_id}", flush=True)
    settings = Settings()
    database = create_database(settings.database_url)
    parsed_run_id = UUID(run_id)

    try:
        async with database.session_factory() as session:
            run_service = ReleaseDiscoveryCandidateService(session)
            run = await run_service.start_run(parsed_run_id)
            if run.status != "running":
                print(
                    f"[worker] release discovery skipped: run_id={run_id} status={run.status}",
                    flush=True,
                )
                return

            anime = await session.scalar(
                select(Anime).where(Anime.id == run.anime_id),
            )
            if anime is None:
                raise ValueError(f"anime not found for discovery run: {run.anime_id}")

            search_title = anime.titles.get("romaji") or anime.title
            anime_id = anime.id

        async with NyaaClient() as client, database.session_factory() as session:
            discovery = ReleaseDiscoveryService(session, client)
            result = await discovery.discover(
                title=search_title,
                anime_id=anime_id,
                fields=(SearchField.TITLE,),
            )
            candidate_service = ReleaseDiscoveryCandidateService(session)
            counts = await candidate_service.record_discovery(parsed_run_id, result)
            await candidate_service.complete_run(parsed_run_id, counts)

        print(
            f"[worker] release discovery completed: run_id={run_id} "
            f"candidates={counts.candidate_count} warnings={counts.warning_count}",
            flush=True,
        )
    except Exception as exc:
        async with database.session_factory() as session:
            await ReleaseDiscoveryCandidateService(session).fail_run(
                parsed_run_id,
                f"{type(exc).__name__}: {exc}",
            )
        print(
            f"[worker] release discovery failed: run_id={run_id} "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
    finally:
        await database.dispose()


@broker.task(task_name=DOWNLOAD_TASK_NAME)
async def download_episode(job_id: str) -> None:
    print(f"[worker] download started: job_id={job_id}", flush=True)
    settings = Settings()
    database = create_database(settings.database_url)
    progress_publisher = RedisJobProgressPublisher(settings.redis_url)
    try:
        api_key = (
            settings.qbittorrent_api_key.get_secret_value()
            if settings.qbittorrent_api_key is not None
            else ""
        )
        async with QBittorrentClient(
            settings.qbittorrent_url,
            api_key,
        ) as torrent_client:
            runner = DownloadRunner(
                state=create_download_state(database),
                torrent_client=torrent_client,
                download_root=settings.download_root,
                on_completed=lambda completed_job_id: _enqueue_media_processing(
                    database,
                    completed_job_id,
                ),
                on_progress=progress_publisher.publish,
            )
            await runner.run(UUID(job_id))
            print(f"[worker] download completed: job_id={job_id}", flush=True)
    finally:
        await progress_publisher.close()
        await database.dispose()


@broker.task(task_name=MEDIA_PROCESSING_TASK_NAME)
async def process_media_job(job_id: str) -> None:
    print(f"[worker] media processing started: job_id={job_id}", flush=True)
    settings = Settings()
    database = create_database(settings.database_url)
    progress_publisher = RedisJobProgressPublisher(settings.redis_url)
    try:
        runner = MediaProcessingRunner(
            state=create_media_processing_state(database.session_factory),
            inspector=FFprobeInspector(),
            download_root=settings.download_root,
            on_progress=progress_publisher.publish,
        )
        parsed_job_id = UUID(job_id)
        await runner.run(parsed_job_id)
        await _enqueue_subtitle_processing(database, parsed_job_id)
        await _enqueue_media_attachment_processing(database, parsed_job_id)
        await _enqueue_media_preparation(database, parsed_job_id)
        print(f"[worker] media processing completed: job_id={job_id}", flush=True)
    finally:
        await progress_publisher.close()
        await database.dispose()


@broker.task(task_name=SUBTITLE_PROCESSING_TASK_NAME)
async def process_subtitle_tracks(asset_id: str) -> None:
    print(f"[worker] subtitle processing started: asset_id={asset_id}", flush=True)
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        ffmpeg_runner = SubprocessFFmpegRunner(
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        runner = SubtitleProcessingRunner(
            state=create_subtitle_processing_state(database.session_factory),
            storage=create_media_storage(settings),
            processor=FFmpegSubtitleProcessor(runner=ffmpeg_runner),
        )
        await runner.run(UUID(asset_id))
        print(f"[worker] subtitle processing completed: asset_id={asset_id}", flush=True)
    finally:
        await database.dispose()


async def _enqueue_subtitle_processing(
    database: Database,
    job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        job = await MediaProcessingJobService(session).get_job(job_id)
        asset = await MediaAssetService(session).get_for_episode(job.episode_id)
        if asset is None or asset.subtitle_processing_ready:
            return
        asset_id = asset.id

    await process_subtitle_tracks.kiq(str(asset_id))


async def _enqueue_media_processing(
    database: Database,
    download_job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        download_job = await DownloadJobService(session).get_job(download_job_id)
        media_service = MediaProcessingJobService(session)
        job = await media_service.create_job(
            download_job.episode_id,
            download_job.id,
        )
        media_job_id = job.id
        media_job_status = job.job_status

    if media_job_status is MediaProcessingJobStatus.COMPLETED:
        return

    await process_media_job.kiq(str(media_job_id))


@broker.task(task_name=MEDIA_ATTACHMENT_PROCESSING_TASK_NAME)
async def process_media_attachments(asset_id: str) -> None:
    settings = Settings()
    database = create_database(settings.database_url)
    try:
        ffmpeg_runner = SubprocessFFmpegRunner(
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        runner = MediaAttachmentProcessingRunner(
            state=create_media_attachment_processing_state(database.session_factory),
            storage=create_media_storage(settings),
            processor=FFmpegAttachmentProcessor(runner=ffmpeg_runner),
        )
        await runner.run(UUID(asset_id))
    finally:
        await database.dispose()


async def _enqueue_media_attachment_processing(
    database: Database,
    job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        job = await MediaProcessingJobService(session).get_job(job_id)
        asset = await MediaAssetService(session).get_for_episode(job.episode_id)
        if asset is None or not asset.attachments_ready or asset.attachment_processing_ready:
            return
        asset_id = asset.id

    await process_media_attachments.kiq(str(asset_id))


@broker.task(task_name=MEDIA_PREPARATION_TASK_NAME)
async def process_media_preparation(job_id: str) -> None:
    print(f"[worker] media preparation started: job_id={job_id}", flush=True)
    settings = Settings()
    database = create_database(settings.database_url)
    progress_publisher = RedisJobProgressPublisher(settings.redis_url)
    try:
        ffmpeg_runner = SubprocessFFmpegRunner(
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        video_encoder = await resolve_video_encoder(
            settings.ffmpeg_video_encoder,
        )
        runner = MediaPreparationRunner(
            state=create_media_preparation_state(database.session_factory),
            storage=create_media_storage(settings),
            inspector=FFprobeInspector(),
            planner=PlayableMediaPlanner(),
            preparation_processor=FFmpegMediaPreparationProcessor(
                runner=ffmpeg_runner,
                video_encoder=video_encoder,
            ),
            playable_processor=FFmpegPlayableMediaProcessor(
                runner=ffmpeg_runner,
                video_encoder=video_encoder,
            ),
            thumbnail_processor=FFmpegThumbnailSpriteProcessor(
                runner=ffmpeg_runner,
            ),
            on_progress=progress_publisher.publish,
        )
        parsed_job_id = UUID(job_id)
        await runner.run(parsed_job_id)
        await _enqueue_media_packaging(database, parsed_job_id)
        print(f"[worker] media preparation completed: job_id={job_id}", flush=True)
    finally:
        await progress_publisher.close()
        await database.dispose()


async def _enqueue_media_preparation(
    database: Database,
    media_processing_job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        processing_job = await MediaProcessingJobService(session).get_job(
            media_processing_job_id,
        )
        asset = await MediaAssetService(session).get_for_episode(
            processing_job.episode_id,
        )
        if asset is None or asset.metadata_updated_at is None:
            return

        asset_id = asset.id
        preparation_job = await MediaPreparationJobService(session).create_job(
            media_asset_id=asset_id,
            source_path=asset.path,
            source_metadata_updated_at=asset.metadata_updated_at,
            thumbnail_ready=asset.thumbnail_ready,
        )
        preparation_job_id = preparation_job.id if preparation_job is not None else None

    if preparation_job_id is None:
        print(
            "[worker] media preparation not enqueued: "
            f"asset_id={asset_id} (active job or already prepared)",
            flush=True,
        )
        return

    print(
        f"[worker] enqueuing media preparation: job_id={preparation_job_id} asset_id={asset_id}",
        flush=True,
    )
    await process_media_preparation.kiq(str(preparation_job_id))


@broker.task(task_name=MEDIA_PACKAGING_TASK_NAME)
async def process_media_packaging(job_id: str) -> None:
    print(f"[worker] media packaging started: job_id={job_id}", flush=True)
    settings = Settings()
    database = create_database(settings.database_url)
    progress_publisher = RedisJobProgressPublisher(settings.redis_url)
    try:
        ffmpeg_runner = SubprocessFFmpegRunner(
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        runner = MediaPackagingRunner(
            state=create_media_packaging_state(database.session_factory),
            storage=create_media_storage(settings),
            processor=FFmpegCMAFProcessor(runner=ffmpeg_runner),
            on_progress=progress_publisher.publish,
        )
        parsed_job_id = UUID(job_id)
        await runner.run(parsed_job_id)
        print(f"[worker] media packaging completed: job_id={job_id}", flush=True)
    finally:
        await progress_publisher.close()
        await database.dispose()


async def _enqueue_media_packaging(
    database: Database,
    media_preparation_job_id: UUID,
) -> None:
    async with database.session_factory() as session:
        preparation_job = await MediaPreparationJobService(session).get_job(
            media_preparation_job_id,
        )
        variant = await MediaVariantService(session).get(
            preparation_job.variant_id,
        )
        if variant is None:
            return

        package_service = MediaStreamingPackageService(session)
        packaging_job = await package_service.create_job(
            media_variant_id=variant.id,
        )
        if packaging_job is not None:
            packaging_job_id = packaging_job.id
            reenqueue = False
        else:
            existing_job = await package_service.get_latest_job(variant.id)
            if existing_job is not None and existing_job.status == "pending":
                packaging_job_id = existing_job.id
                reenqueue = True
            else:
                packaging_job_id = None
                reenqueue = False

    if packaging_job_id is None:
        return

    if reenqueue:
        print(
            f"[worker] re-enqueuing pending media packaging job: job_id={packaging_job_id}",
            flush=True,
        )

    await process_media_packaging.kiq(str(packaging_job_id))
