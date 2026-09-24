from animedownloader_config import Settings
from animedownloader_database import create_database
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
