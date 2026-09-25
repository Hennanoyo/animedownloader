import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid7

import pytest
from animedownloader_api.dependencies import get_job_progress_hub
from animedownloader_api.routes.job_events import router
from animedownloader_config import JobProgressEvent, JobProgressReadyEvent
from animedownloader_worker.progress import (
    RedisJobProgressPublisher,
    emit_job_progress,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _published_list() -> list[tuple[str, str]]:
    return []


@dataclass
class FakeRedisPublisher:
    published: list[tuple[str, str]] = field(default_factory=_published_list)
    closed: bool = False

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        return 1

    async def aclose(self) -> None:
        self.closed = True


@dataclass
class FakeRedisFailure:
    async def publish(self, channel: str, message: str) -> int:
        raise RuntimeError("redis unavailable")

    async def aclose(self) -> None:
        return


@dataclass
class FakeSubscription:
    event: JobProgressEvent


@dataclass
class FakeHub:
    event: JobProgressEvent
    subscription: FakeSubscription | None = None

    async def wait_until_ready(self, timeout: float = 5.0) -> bool:
        return True

    def subscribe(self, job_type: str | None) -> FakeSubscription:
        self.subscription = FakeSubscription(self.event)
        return self.subscription

    async def events(
        self,
        subscription: FakeSubscription,
    ) -> AsyncIterator[JobProgressEvent]:
        yield subscription.event

    def unsubscribe(self, subscription: FakeSubscription) -> None:
        assert subscription is self.subscription


def make_event() -> JobProgressEvent:
    return JobProgressEvent(
        job_type="media-processing",
        job_id=uuid7(),
        status="downloading",
        progress_percent=50,
        stage="processing",
        downloaded_bytes=500,
        total_bytes=1000,
        emitted_at=datetime.now(UTC),
    )


def test_progress_event_rejects_invalid_percent() -> None:
    with pytest.raises(ValueError):
        JobProgressEvent(
            job_type="download",
            job_id=uuid7(),
            status="downloading",
            progress_percent=101,
            emitted_at=datetime.now(UTC),
        )


def test_progress_publisher_serializes_event() -> None:
    client = FakeRedisPublisher()
    publisher = RedisJobProgressPublisher("redis://unused", client=client)
    event = make_event()

    asyncio.run(publisher.publish(event))
    asyncio.run(publisher.close())

    assert client.published
    channel, payload = client.published[0]
    assert channel == "animedownloader:job-progress"
    assert JobProgressEvent.model_validate_json(payload) == event
    assert client.closed



@pytest.mark.anyio
async def test_emit_job_progress_builds_event() -> None:
    client = FakeRedisPublisher()
    publisher = RedisJobProgressPublisher("redis://unused", client=client)

    async def callback(event: JobProgressEvent) -> None:
        await publisher.publish(event)

    job_id = uuid7()
    await emit_job_progress(
        callback,
        job_type="media-processing",
        job_id=job_id,
        status="processing",
        progress_percent=0,
        stage="processing",
    )

    event = JobProgressEvent.model_validate_json(client.published[0][1])
    assert event.job_type == "media-processing"
    assert event.job_id == job_id
    assert event.status == "processing"
    assert event.progress_percent == 0
    assert event.stage == "processing"

def test_progress_publisher_does_not_raise_when_redis_fails() -> None:
    client = FakeRedisFailure()
    publisher = RedisJobProgressPublisher("redis://unused", client=client)

    asyncio.run(publisher.publish(make_event()))


def test_progress_websocket_sends_ready_and_event() -> None:
    event = make_event()
    hub = FakeHub(event)
    app = FastAPI()
    app.dependency_overrides[get_job_progress_hub] = lambda: hub
    app.include_router(router)

    with TestClient(app) as client, client.websocket_connect(
        "/api/job-events/ws?job_type=media-processing",
    ) as websocket:
        ready = JobProgressReadyEvent.model_validate_json(
            websocket.receive_text(),
        )
        received = JobProgressEvent.model_validate_json(
            websocket.receive_text(),
        )

    assert ready.job_type == "media-processing"
    assert received == event
