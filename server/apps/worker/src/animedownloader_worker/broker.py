from animedownloader_config import Settings
from taskiq import AsyncBroker
from taskiq_redis import RedisStreamBroker

settings = Settings()

broker: AsyncBroker = RedisStreamBroker(
    url=settings.redis_url,
)


@broker.task
async def healthcheck() -> str:
    return "ok"
