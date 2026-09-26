from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from uuid import UUID

from animedownloader_api.release_candidates import (
    ReleaseDiscoveryCandidateService,
    ReleaseDiscoveryRun,
    ReleaseDiscoveryRunStatus,
    ReleaseDiscoverySchedule,
)
from animedownloader_database import Database
from sqlalchemy import select

from .task_queue import ReleaseDiscoveryTaskDispatcher


class ReleaseDiscoveryScheduler:
    def __init__(
        self,
        database: Database,
        dispatcher: ReleaseDiscoveryTaskDispatcher,
        *,
        poll_seconds: float = 15.0,
    ) -> None:
        self._database = database
        self._dispatcher = dispatcher
        self._poll_seconds = poll_seconds
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(
            self._run(),
            name="release-discovery-scheduler",
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await self.run_due()
            except Exception as exc:
                print(
                    "[api] release discovery scheduler failed: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

            with suppress(TimeoutError):
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=self._poll_seconds,
                )

    async def enqueue_run(self, run_id: UUID) -> None:
        await self._dispatcher.enqueue(run_id)

    async def run_due(self, *, now: datetime | None = None, limit: int = 8) -> int:
        claimed = await self._claim_due_runs(
            now=now or datetime.now(UTC),
            limit=limit,
        )
        for run in claimed:
            try:
                await self.enqueue_run(run.id)
            except Exception as exc:
                async with self._database.session_factory() as session:
                    await ReleaseDiscoveryCandidateService(session).fail_run(
                        run.id,
                        f"Failed to enqueue discovery task: {type(exc).__name__}: {exc}",
                    )
        return len(claimed)

    async def _claim_due_runs(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[ReleaseDiscoveryRun]:
        async with self._database.session_factory() as session, session.begin():
                rows = await session.scalars(
                    select(ReleaseDiscoverySchedule)
                    .where(
                        ReleaseDiscoverySchedule.enabled.is_(True),
                        ReleaseDiscoverySchedule.next_run_at.is_not(None),
                        ReleaseDiscoverySchedule.next_run_at <= now,
                    )
                    .order_by(ReleaseDiscoverySchedule.next_run_at, ReleaseDiscoverySchedule.anime_id)
                    .limit(limit)
                    .with_for_update(skip_locked=True),
                )
                schedules = list(rows.all())

                claimed: list[ReleaseDiscoveryRun] = []
                for schedule in schedules:
                    active = await session.scalar(
                        select(ReleaseDiscoveryRun.id)
                        .where(
                            ReleaseDiscoveryRun.anime_id == schedule.anime_id,
                            ReleaseDiscoveryRun.status.in_(
                                [
                                    ReleaseDiscoveryRunStatus.QUEUED.value,
                                    ReleaseDiscoveryRunStatus.RUNNING.value,
                                ],
                            ),
                        )
                        .limit(1),
                    )
                    if active is not None:
                        continue

                    scheduled_for = schedule.next_run_at or now
                    schedule.next_run_at = now + timedelta(
                        minutes=schedule.interval_minutes,
                    )
                    run = ReleaseDiscoveryRun(
                        anime_id=schedule.anime_id,
                        scheduled_for=scheduled_for,
                    )
                    session.add(run)
                    await session.flush()
                    claimed.append(run)

                return claimed


