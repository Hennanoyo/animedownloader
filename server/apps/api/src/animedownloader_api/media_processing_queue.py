from uuid import UUID

from animedownloader_media_processing import MEDIA_PROCESSING_TASK_NAME
from taskiq import AsyncBroker


async def _media_processing_task_placeholder(job_id: str) -> None:
    raise RuntimeError(
        f"Media processing task {job_id} must be executed by the worker application",
    )


class MediaProcessingTaskDispatcher:
    def __init__(self, broker: AsyncBroker) -> None:
        self._task = broker.register_task(
            _media_processing_task_placeholder,
            task_name=MEDIA_PROCESSING_TASK_NAME,
        )

    async def enqueue(self, job_id: UUID) -> None:
        await self._task.kiq(str(job_id))
