from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.db.base import Base
from app.db.session import create_session_factory
from app.repositories.delivery_jobs_repo import DeliveryJobsRepo
from app.services.lease_heartbeat import LeaseHeartbeatService


async def _create_session_factory():
    _, session_factory = create_session_factory(Settings(database_url="sqlite+aiosqlite:///:memory:"))
    async with session_factory() as session:
        async with session.bind.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    return session_factory


@pytest.mark.asyncio
async def test_extend_lease_updates_expiry():
    session_factory = await _create_session_factory()
    async with session_factory() as session:
        repo = DeliveryJobsRepo(session)
        job = await repo.enqueue(
            route_id="route-1",
            target_platform="telegram",
            target_chat_id="chat-1",
            origin_platform="telegram",
            origin_chat_id="source-chat",
            origin_message_id="source-message",
            payload={"route": {}, "post": {}},
            max_attempts=3,
        )
        acquired = await repo.acquire_due_jobs(limit=1, lock_token="tok-1", lease_seconds=1)
        assert acquired
        before = acquired[0]["lock_expires_at"]
        extended = await repo.extend_lease(job["id"], lock_token="tok-1", lease_seconds=30)
        assert extended is True
        rows = await repo.list_all()
        after = next(row for row in rows if row["id"] == job["id"])["lock_expires_at"]
        assert after > before


@pytest.mark.asyncio
async def test_heartbeat_service_extends_running_job():
    session_factory = await _create_session_factory()
    async with session_factory() as session:
        repo = DeliveryJobsRepo(session)
        job = await repo.enqueue(
            route_id="route-1",
            target_platform="telegram",
            target_chat_id="chat-1",
            origin_platform="telegram",
            origin_chat_id="source-chat",
            origin_message_id="source-message",
            payload={"route": {}, "post": {}},
            max_attempts=3,
        )
        acquired = await repo.acquire_due_jobs(limit=1, lock_token="tok-1", lease_seconds=1)
        await session.commit()
        before = acquired[0]["lock_expires_at"]

    container = SimpleNamespace(session_factory=session_factory)
    service = LeaseHeartbeatService(container=container, poll_interval_seconds=0.05, lease_seconds=2)
    handle = service.start(job_id=job["id"], lock_token="tok-1")
    await asyncio.sleep(0.12)
    await handle.stop()

    async with session_factory() as session:
        rows = await DeliveryJobsRepo(session).list_all()
        after = next(row for row in rows if row["id"] == job["id"])["lock_expires_at"]

    assert after > before
