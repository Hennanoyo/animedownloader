from datetime import UTC, datetime
from typing import Annotated

from animedownloader_config import JobProgressReadyEvent
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from animedownloader_api.dependencies import get_job_progress_hub
from animedownloader_api.job_progress import JobProgressHub

router = APIRouter(prefix="/api/job-events", tags=["job-events"])


@router.websocket("/ws")
async def job_progress_websocket(
    websocket: WebSocket,
    hub: Annotated[JobProgressHub, Depends(get_job_progress_hub)],
    job_type: Annotated[str | None, Query()] = None,
) -> None:
    if not await hub.wait_until_ready():
        await websocket.accept()
        await websocket.close(code=1013)
        return

    await websocket.accept()
    subscription = hub.subscribe(job_type)
    ready = JobProgressReadyEvent(
        job_type=job_type or "all",
        emitted_at=datetime.now(UTC),
    )
    try:
        await websocket.send_text(ready.model_dump_json())
        async for event in hub.events(subscription):
            await websocket.send_text(event.model_dump_json())
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(subscription)
