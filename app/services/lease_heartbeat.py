from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.repositories.delivery_jobs_repo import DeliveryJobsRepo

if TYPE_CHECKING:
    from app.dependencies import Container

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LeaseHeartbeatHandle:
    task: asyncio.Task | None

    async def stop(self) -> None:
        if self.task is None:
            return
        self.task.cancel()
        with suppress(asyncio.CancelledError):
            await self.task
        self.task = None


class LeaseHeartbeatService:
    def __init__(
        self,
        *,
        container: "Container",
        poll_interval_seconds: float,
        lease_seconds: int,
    ) -> None:
        self.container = container
        self.poll_interval_seconds = poll_interval_seconds
        self.lease_seconds = lease_seconds

    def start(self, *, job_id: int, lock_token: str) -> LeaseHeartbeatHandle:
        task = asyncio.create_task(
            self._run(job_id=job_id, lock_token=lock_token),
            name=f"delivery-job-heartbeat-{job_id}",
        )
        return LeaseHeartbeatHandle(task=task)

    async def _run(self, *, job_id: int, lock_token: str) -> None:
        while True:
            try:
                await asyncio.sleep(self.poll_interval_seconds)
                async with self.container.session_factory() as session:
                    repo = DeliveryJobsRepo(session)
                    extended = await repo.extend_lease(
                        job_id,
                        lock_token=lock_token,
                        lease_seconds=self.lease_seconds,
                    )
                    await session.commit()
                if not extended:
                    logger.info("Lease heartbeat stopped because job lease is no longer owned", extra={"job_id": job_id})
                    return
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Lease heartbeat failed", extra={"job_id": job_id})
