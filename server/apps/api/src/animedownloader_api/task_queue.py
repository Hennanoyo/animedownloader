from uuid import UUID

from taskiq import AsyncBroker
from taskiq_redis import RedisStreamBroker

RELEASE_DISCOVERY_TASK_NAME = "release-discovery.run"


async def _release_discovery_task_placeholder(run_id: str) -> None:
    raise RuntimeError(
        f"Release discovery task {run_id} must be executed by the worker application",
    )


class ReleaseDiscoveryTaskDispatcher:
    def __init__(self, broker: AsyncBroker) -> None:
        self._task = broker.register_task(
            _release_discovery_task_placeholder,
            task_name=RELEASE_DISCOVERY_TASK_NAME,
        )

    async def enqueue(self, run_id: UUID) -> None:
        await self._task.kiq(str(run_id))


def create_task_broker(redis_url: str) -> AsyncBroker:
    return RedisStreamBroker(url=redis_url)
