from animedownloader_config import Settings
from taskiq import AsyncBroker
from taskiq_redis import RedisStreamBroker

settings = Settings()

broker: AsyncBroker = RedisStreamBroker(
    url=settings.redis_url,
    xread_block=2000,
    socket_connect_timeout=5.0,
    unacknowledged_lock_timeout=30.0,
)


@broker.task
async def healthcheck() -> str:
    return "ok"
