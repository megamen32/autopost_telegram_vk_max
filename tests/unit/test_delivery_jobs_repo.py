from datetime import datetime, timedelta, timezone

import pytest

from app.db.base import Base
from app.db.session import create_session_factory
from app.config import Settings
from app.repositories.delivery_jobs_repo import DeliveryJobsRepo


@pytest.mark.asyncio
async def test_delivery_jobs_dead_letter_and_reclaim() -> None:
    _, session_factory = create_session_factory(Settings(database_url="sqlite+aiosqlite:///:memory:"))

    async with session_factory() as session:
        async with session.bind.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        repo = DeliveryJobsRepo(session)
        await repo.enqueue(
            route_id="r1",
            target_platform="telegram",
            target_chat_id="c1",
            origin_platform="vk",
            origin_chat_id="o1",
            origin_message_id="m1",
            payload={"route": {}, "post": {}},
            max_attempts=3,
        )
        jobs = await repo.acquire_due_jobs(limit=1, lock_token="abc", lease_seconds=1)
        assert jobs[0]["status"] == "running"
        await repo.mark_dead_letter(1, lock_token="abc", attempts=1, last_error="boom", error_code="non_retryable")
        await session.commit()

    async with session_factory() as session:
        repo = DeliveryJobsRepo(session)
        rows = await repo.list_all()
        assert rows[0]["status"] == "dead_letter"

    async with session_factory() as session:
        repo = DeliveryJobsRepo(session)
        await repo.enqueue(
            route_id="r2",
            target_platform="telegram",
            target_chat_id="c2",
            origin_platform="vk",
            origin_chat_id="o2",
            origin_message_id="m2",
            payload={"route": {}, "post": {}},
            max_attempts=3,
        )
        jobs = await repo.acquire_due_jobs(limit=1, lock_token="stale", lease_seconds=1)
        await repo.mark_retry(2, lock_token="stale", attempts=1, next_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=5), last_error="retry", error_code="transient_error")
        await session.commit()

    async with session_factory() as session:
        repo = DeliveryJobsRepo(session)
        jobs = await repo.acquire_due_jobs(limit=1, lock_token="fresh", lease_seconds=1)
        assert jobs[0]["id"] == 2
