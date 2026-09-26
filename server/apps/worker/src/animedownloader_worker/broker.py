from uuid import UUID

from animedownloader_config import Settings
from animedownloader_database import create_database
from animedownloader_api.release_candidate_automation import ReleaseCandidateAutomationService
from animedownloader_api.task_queue import RELEASE_CANDIDATE_AUTOMATION_TASK_NAME
from animedownloader_media_processing import (
    MEDIA_PACKAGING_TASK_NAME,
    MEDIA_PREPARATION_TASK_NAME,
    MEDIA_PROCESSING_TASK_NAME,
    MediaPreparationJobService,
    MediaProcessingJobService,
    MediaStreamingPackageService,
)
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState
from taskiq_redis import RedisStreamBroker

from .source_recovery import recover_completed_download_handoffs

settings = Settings()

broker: AsyncBroker = RedisStreamBroker(
    url=settings.redis_url,
    xread_block=2000,
    socket_connect_timeout=5.0,
    socket_timeout=None,
    unacknowledged_lock_timeout=30.0,
)


@broker.task
async def healthcheck() -> str:
    return "ok"


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def recover_active_media_jobs(_state: TaskiqState) -> None:
    print("[worker] startup media job recovery started", flush=True)
    database = create_database(settings.database_url)
    recovered = 0
    try:
        async with database.session_factory() as session:
            processing_jobs = await MediaProcessingJobService(session).get_active_jobs()
            preparation_jobs = await MediaPreparationJobService(session).get_active_jobs()
            packaging_jobs = await MediaStreamingPackageService(session).get_active_jobs()

        recovery_targets = (
            (MEDIA_PROCESSING_TASK_NAME, processing_jobs),
            (MEDIA_PREPARATION_TASK_NAME, preparation_jobs),
            (MEDIA_PACKAGING_TASK_NAME, packaging_jobs),
        )

        for task_name, jobs in recovery_targets:
            task = broker.find_task(task_name)
            if task is None:
                print(
                    "[worker] startup media job recovery skipped: "
                    f"task not registered task_name={task_name}",
                    flush=True,
                )
                continue

            for job in jobs:
                await task.kiq(str(job.id))
                recovered += 1
                print(
                    "[worker] recovered media job: "
                    f"task={task_name} job_id={job.id} status={job.status}",
                    flush=True,
                )
    except Exception as exc:
        print(
            f"[worker] startup media job recovery failed: {type(exc).__name__}: {exc}",
            flush=True,
        )
        raise
    finally:
        await database.dispose()

    print(
        f"[worker] startup media job recovery completed: recovered={recovered}",
        flush=True,
    )

    automation_task = broker.find_task(RELEASE_CANDIDATE_AUTOMATION_TASK_NAME)
    if automation_task is not None:
        automation_database = create_database(settings.database_url)
        try:
            async with automation_database.session_factory() as session:
                recovery_anime_ids = await ReleaseCandidateAutomationService(
                    session,
                ).list_recovery_anime_ids()
            for anime_id in recovery_anime_ids:
                await automation_task.kiq(str(anime_id))
                print(
                    "[worker] recovered release candidate automation: "
                    f"anime_id={anime_id}",
                    flush=True,
                )
        finally:
            await automation_database.dispose()

    media_task = broker.find_task(MEDIA_PROCESSING_TASK_NAME)
    if media_task is None:
        print(
            "[worker] completed download handoff recovery skipped: "
            "media-processing task not registered",
            flush=True,
        )
        return

    async def enqueue_media_processing(job_id: UUID) -> None:
        await media_task.kiq(str(job_id))

    handoff_database = create_database(settings.database_url)
    try:
        recovered_handoffs, unresolved_sources = (
            await recover_completed_download_handoffs(
                handoff_database,
                download_root=settings.download_root,
                enqueue_media_processing=enqueue_media_processing,
            )
        )
    except Exception as exc:
        print(
            "[worker] completed download handoff recovery failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        raise
    finally:
        await handoff_database.dispose()

    print(
        "[worker] completed download handoff recovery completed: "
        f"recovered={recovered_handoffs} unresolved={unresolved_sources}",
        flush=True,
    )
