from __future__ import annotations

import logging
from typing import Protocol, cast

from animedownloader_config import JOB_PROGRESS_CHANNEL, JobProgressEvent
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisPublisher(Protocol):
    async def publish(self, channel: str, message: str) -> int: ...

    async def aclose(self) -> None: ...


class RedisJobProgressPublisher:
    def __init__(
        self,
        redis_url: str,
        *,
        client: RedisPublisher | None = None,
    ) -> None:
        self._redis: RedisPublisher = client or cast(
            RedisPublisher,
            Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=0.5,
            ),
        )

    async def publish(self, event: JobProgressEvent) -> None:
        try:
            await self._redis.publish(
                JOB_PROGRESS_CHANNEL,
                event.model_dump_json(),
            )
        except Exception:
            logger.warning(
                "Failed to publish job progress event: job_id=%s status=%s",
                event.job_id,
                event.status,
                exc_info=True,
            )

    async def close(self) -> None:
        try:
            await self._redis.aclose()
        except Exception:
            logger.warning(
                "Failed to close job progress Redis client",
                exc_info=True,
            )
