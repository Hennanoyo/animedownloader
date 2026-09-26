from uuid import UUID

from animedownloader_download import DOWNLOAD_TASK_NAME
from taskiq import AsyncBroker
from taskiq_redis import RedisStreamBroker

RELEASE_DISCOVERY_TASK_NAME = "release-discovery.run"


async def _download_task_placeholder(job_id: str) -> None:
    raise RuntimeError(f"Download task {job_id} must be executed by the worker application")


async def _release_discovery_task_placeholder(run_id: str) -> None:
    raise RuntimeError(
        f"Release discovery task {run_id} must be executed by the worker application",
    )


class DownloadTaskDispatcher:
    def __init__(self, broker: AsyncBroker) -> None:
        self._task = broker.register_task(
            _download_task_placeholder,
            task_name=DOWNLOAD_TASK_NAME,
        )

    async def enqueue(self, job_id: UUID) -> None:
        await self._task.kiq(str(job_id))


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
