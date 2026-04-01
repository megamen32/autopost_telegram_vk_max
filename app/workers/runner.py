from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.workers.tasks import process_due_delivery_jobs

if TYPE_CHECKING:
    from app.dependencies import Container

logger = logging.getLogger(__name__)


class DeliveryWorkerRunner:
    def __init__(self, container: "Container", *, poll_interval_seconds: float) -> None:
        self.container = container
        self.poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run_loop(), name="delivery-worker-runner")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stopping.is_set():
            try:
                processed = await process_due_delivery_jobs(self.container)
                sleep_for = 0.05 if processed else self.poll_interval_seconds
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Delivery worker loop failed")
                sleep_for = self.poll_interval_seconds
            await asyncio.sleep(sleep_for)
