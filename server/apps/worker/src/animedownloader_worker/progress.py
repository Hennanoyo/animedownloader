from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from animedownloader_config import JOB_PROGRESS_CHANNEL, JobProgressEvent
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

JobProgressCallback = Callable[[JobProgressEvent], Awaitable[None]]


async def emit_job_progress(
    callback: JobProgressCallback | None,
    *,
    job_type: str,
    job_id: UUID,
    status: str,
    progress_percent: float | None = None,
    error_message: str | None = None,
) -> None:
    if callback is None:
        return
    event = JobProgressEvent(
        job_type=job_type,
        job_id=job_id,
        status=status,
        progress_percent=progress_percent,
        downloaded_bytes=None,
        total_bytes=None,
        error_message=error_message,
        emitted_at=datetime.now(UTC),
    )
    try:
        await callback(event)
    except Exception:
        logger.exception(
            "Failed to publish progress event: job_type=%s job_id=%s status=%s",
            job_type,
            job_id,
            status,
        )


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
            Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
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
