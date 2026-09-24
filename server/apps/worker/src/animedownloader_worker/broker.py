from animedownloader_config import Settings
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
async def wake_stream_recovery(_state: TaskiqState) -> None:
    await healthcheck.kiq()
    print("[worker] Redis stream recovery wake-up queued", flush=True)
