from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol, cast

from animedownloader_config import JOB_PROGRESS_CHANNEL, JobProgressEvent
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_RETRY_DELAY = 2.0
_QUEUE_SIZE = 32


class RedisPubSub(Protocol):
    async def subscribe(self, *channels: str) -> object: ...

    async def get_message(
        self,
        *,
        ignore_subscribe_messages: bool = True,
        timeout: float | None = None,
    ) -> dict[str, object] | None: ...

    async def aclose(self) -> None: ...


class RedisClient(Protocol):
    def pubsub(self, **kwargs: object) -> RedisPubSub: ...

    async def aclose(self) -> None: ...


@dataclass(eq=False, slots=True)
class JobProgressSubscription:
    job_type: str | None
    queue: asyncio.Queue[JobProgressEvent | None]


class JobProgressHub:
    def __init__(
        self,
        redis_url: str,
        *,
        client: RedisClient | None = None,
    ) -> None:
        self._redis: RedisClient = client or cast(
            RedisClient,
            Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=None,
            ),
        )
        self._subscriptions: set[JobProgressSubscription] = set()
        self._stop = asyncio.Event()
        self._redis_ready = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        self._redis_ready.clear()
        self._disconnect_subscribers()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._redis.aclose()

    async def wait_until_ready(self, timeout: float = 5.0) -> bool:
        if self._redis_ready.is_set():
            return True
        try:
            await asyncio.wait_for(self._redis_ready.wait(), timeout=timeout)
        except TimeoutError:
            return False
        return True

    def subscribe(self, job_type: str | None) -> JobProgressSubscription:
        subscription = JobProgressSubscription(
            job_type=job_type,
            queue=asyncio.Queue(maxsize=_QUEUE_SIZE),
        )
        self._subscriptions.add(subscription)
        return subscription

    def unsubscribe(self, subscription: JobProgressSubscription) -> None:
        self._subscriptions.discard(subscription)

    async def events(
        self,
        subscription: JobProgressSubscription,
    ) -> AsyncIterator[JobProgressEvent]:
        while True:
            event = await subscription.queue.get()
            if event is None:
                return
            yield event

    async def _run(self) -> None:
        while not self._stop.is_set():
            pubsub = self._redis.pubsub()
            try:
                await pubsub.subscribe(JOB_PROGRESS_CHANNEL)
                self._redis_ready.set()
                while not self._stop.is_set():
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )
                    if message is None or message.get("type") != "message":
                        continue
                    payload = message.get("data")
                    if not isinstance(payload, str):
                        continue
                    try:
                        event = JobProgressEvent.model_validate_json(payload)
                    except Exception:
                        logger.warning("Ignoring invalid job progress event", exc_info=True)
                        continue
                    self._dispatch(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                self._redis_ready.clear()
                self._disconnect_subscribers()
                logger.warning(
                    "Job progress Redis subscription failed; retrying",
                    exc_info=True,
                )
                with suppress(TimeoutError):
                    await asyncio.wait_for(self._stop.wait(), timeout=_RETRY_DELAY)
            finally:
                await pubsub.aclose()
                self._redis_ready.clear()

    def _dispatch(self, event: JobProgressEvent) -> None:
        for subscription in tuple(self._subscriptions):
            if (
                subscription.job_type is not None
                and subscription.job_type != event.job_type
            ):
                continue
            try:
                subscription.queue.put_nowait(event)
            except asyncio.QueueFull:
                with suppress(asyncio.QueueEmpty):
                    subscription.queue.get_nowait()
                subscription.queue.put_nowait(event)

    def _disconnect_subscribers(self) -> None:
        for subscription in tuple(self._subscriptions):
            while True:
                try:
                    subscription.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            with suppress(asyncio.QueueFull):
                subscription.queue.put_nowait(None)
