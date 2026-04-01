from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, and_, or_, select

from app.db.models import DeliveryJobORM
from app.repositories.base import SQLAlchemyRepo


class DeliveryJobsRepo(SQLAlchemyRepo):
    async def enqueue(
        self,
        *,
        route_id: str,
        target_platform: str,
        target_chat_id: str,
        origin_platform: str,
        origin_chat_id: str,
        origin_message_id: str,
        payload: dict,
        max_attempts: int,
    ) -> dict:
        row = DeliveryJobORM(
            status="pending",
            route_id=route_id,
            target_platform=target_platform,
            target_chat_id=target_chat_id,
            origin_platform=origin_platform,
            origin_chat_id=origin_chat_id,
            origin_message_id=origin_message_id,
            payload_json=json.dumps(payload, ensure_ascii=False),
            max_attempts=max_attempts,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return self._to_dict(row)

    async def acquire_due_jobs(self, *, limit: int, lock_token: str, lease_seconds: int) -> list[dict]:
        dialect_name = self.session.bind.dialect.name if self.session.bind is not None else "unknown"
        if dialect_name == "postgresql":
            return await self._acquire_due_jobs_postgres(limit=limit, lock_token=lock_token, lease_seconds=lease_seconds)
        return await self._acquire_due_jobs_generic(limit=limit, lock_token=lock_token, lease_seconds=lease_seconds)

    async def _acquire_due_jobs_postgres(self, *, limit: int, lock_token: str, lease_seconds: int) -> list[dict]:
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=lease_seconds)
        base_stmt: Select = (
            select(DeliveryJobORM)
            .where(
                or_(
                    and_(
                        DeliveryJobORM.status.in_(["pending", "retrying"]),
                        DeliveryJobORM.available_at <= now,
                    ),
                    and_(
                        DeliveryJobORM.status == "running",
                        DeliveryJobORM.lock_expires_at.is_not(None),
                        DeliveryJobORM.lock_expires_at < now,
                    ),
                )
            )
            .order_by(DeliveryJobORM.available_at.asc(), DeliveryJobORM.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = (await self.session.execute(base_stmt)).scalars().all()
        result = []
        for row in rows:
            row.status = "running"
            row.lock_token = lock_token
            row.locked_at = now
            row.lock_expires_at = lease_until
            result.append(self._to_dict(row))
        await self.session.flush()
        return result

    async def _acquire_due_jobs_generic(self, *, limit: int, lock_token: str, lease_seconds: int) -> list[dict]:
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=lease_seconds)
        stmt: Select = (
            select(DeliveryJobORM)
            .where(
                or_(
                    and_(
                        DeliveryJobORM.status.in_(["pending", "retrying"]),
                        DeliveryJobORM.available_at <= now,
                    ),
                    and_(
                        DeliveryJobORM.status == "running",
                        DeliveryJobORM.lock_expires_at.is_not(None),
                        DeliveryJobORM.lock_expires_at < now,
                    ),
                )
            )
            .order_by(DeliveryJobORM.available_at.asc(), DeliveryJobORM.id.asc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        result = []
        for row in rows:
            row.status = "running"
            row.lock_token = lock_token
            row.locked_at = now
            row.lock_expires_at = lease_until
            result.append(self._to_dict(row))
        await self.session.flush()
        return result

    async def extend_lease(self, job_id: int, *, lock_token: str, lease_seconds: int) -> bool:
        row = await self.session.get(DeliveryJobORM, job_id)
        if row is None or row.lock_token != lock_token or row.status != "running":
            return False
        now = datetime.now(timezone.utc)
        row.lock_expires_at = now + timedelta(seconds=lease_seconds)
        row.updated_at = now
        await self.session.flush()
        return True

    async def mark_succeeded(self, job_id: int, *, lock_token: str) -> None:
        row = await self.session.get(DeliveryJobORM, job_id)
        if row is None or row.lock_token != lock_token:
            return
        now = datetime.now(timezone.utc)
        row.status = "succeeded"
        row.completed_at = now
        row.locked_at = None
        row.lock_expires_at = None
        row.lock_token = None
        row.updated_at = now
        await self.session.flush()

    async def mark_retry(
        self,
        job_id: int,
        *,
        lock_token: str,
        attempts: int,
        next_attempt_at: datetime,
        last_error: str,
        error_code: str | None,
    ) -> None:
        row = await self.session.get(DeliveryJobORM, job_id)
        if row is None or row.lock_token != lock_token:
            return
        row.status = "retrying"
        row.attempts = attempts
        row.next_attempt_at = next_attempt_at
        row.available_at = next_attempt_at
        row.last_error = last_error
        row.last_error_code = error_code
        row.locked_at = None
        row.lock_expires_at = None
        row.lock_token = None
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def mark_dead_letter(
        self,
        job_id: int,
        *,
        lock_token: str,
        attempts: int,
        last_error: str,
        error_code: str | None,
    ) -> None:
        row = await self.session.get(DeliveryJobORM, job_id)
        if row is None or row.lock_token != lock_token:
            return
        now = datetime.now(timezone.utc)
        row.status = "dead_letter"
        row.attempts = attempts
        row.last_error = last_error
        row.last_error_code = error_code
        row.dead_lettered_at = now
        row.locked_at = None
        row.lock_expires_at = None
        row.lock_token = None
        row.updated_at = now
        await self.session.flush()

    async def requeue_stale_running_jobs(self) -> int:
        now = datetime.now(timezone.utc)
        stmt: Select = select(DeliveryJobORM).where(
            DeliveryJobORM.status == "running",
            DeliveryJobORM.lock_expires_at.is_not(None),
            DeliveryJobORM.lock_expires_at < now,
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        count = 0
        for row in rows:
            row.status = "retrying"
            row.lock_token = None
            row.locked_at = None
            row.lock_expires_at = None
            row.available_at = now
            count += 1
        await self.session.flush()
        return count


    async def requeue_job(self, job_id: int) -> bool:
        row = await self.session.get(DeliveryJobORM, job_id)
        if row is None:
            return False
        now = datetime.now(timezone.utc)
        row.status = "retrying"
        row.available_at = now
        row.next_attempt_at = now
        row.lock_token = None
        row.locked_at = None
        row.lock_expires_at = None
        row.dead_lettered_at = None
        row.last_error = None
        row.last_error_code = None
        row.updated_at = now
        await self.session.flush()
        return True

    async def list_all(self) -> list[dict]:
        rows = (await self.session.execute(select(DeliveryJobORM).order_by(DeliveryJobORM.id.asc()))).scalars().all()
        return [self._to_dict(row) for row in rows]

    def _to_dict(self, row: DeliveryJobORM) -> dict:
        return {
            "id": row.id,
            "status": row.status,
            "route_id": row.route_id,
            "target_platform": row.target_platform,
            "target_chat_id": row.target_chat_id,
            "origin_platform": row.origin_platform,
            "origin_chat_id": row.origin_chat_id,
            "origin_message_id": row.origin_message_id,
            "payload": json.loads(row.payload_json),
            "attempts": row.attempts,
            "max_attempts": row.max_attempts,
            "next_attempt_at": row.next_attempt_at.isoformat() if row.next_attempt_at else None,
            "available_at": row.available_at.isoformat() if row.available_at else None,
            "last_error": row.last_error,
            "last_error_code": row.last_error_code,
            "lock_token": row.lock_token,
            "locked_at": row.locked_at.isoformat() if row.locked_at else None,
            "lock_expires_at": row.lock_expires_at.isoformat() if row.lock_expires_at else None,
            "dead_lettered_at": row.dead_lettered_at.isoformat() if row.dead_lettered_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
