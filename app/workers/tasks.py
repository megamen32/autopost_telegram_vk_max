from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from app.domain.enums import Platform
from app.repositories.delivery_jobs_repo import DeliveryJobsRepo
from app.repositories.message_links_repo import MessageLinksRepo
from app.services.lease_heartbeat import LeaseHeartbeatService
from app.services.retry_policy import RetryPolicyService
from app.utils.serialization import route_from_dict, unified_post_from_dict

if TYPE_CHECKING:
    from app.dependencies import Container

from app.utils.logging import get_logger

logger = get_logger("autopost_sync.worker")


async def process_due_delivery_jobs(container: "Container") -> int:
    processed = 0
    lock_token = uuid.uuid4().hex
    async with container.session_factory() as session:
        repo = DeliveryJobsRepo(session)
        jobs = await repo.acquire_due_jobs(
            limit=container.delivery_worker_batch_size,
            lock_token=lock_token,
            lease_seconds=container.delivery_job_lease_seconds,
        )
        await session.commit()

    for job in jobs:
        async with container.session_factory() as session:
            jobs_repo = DeliveryJobsRepo(session)
            message_links_repo = MessageLinksRepo(session)
            retry_policy = RetryPolicyService(
                base_delay_seconds=container.delivery_retry_base_seconds,
                max_delay_seconds=container.delivery_retry_max_seconds,
                jitter_seconds=container.delivery_retry_jitter_seconds,
            )
            heartbeat = LeaseHeartbeatService(
                container=container,
                poll_interval_seconds=container.delivery_job_heartbeat_interval_seconds,
                lease_seconds=container.delivery_job_lease_seconds,
            ).start(job_id=job["id"], lock_token=job["lock_token"])
            try:
                payload = job["payload"]
                route = route_from_dict(payload["route"])
                post = unified_post_from_dict(payload["post"])
                adapter = container.adapter_registry.get_by_instance(route.target_adapter_id)
                logger.info("delivery job started | %s", {"job_id": job["id"], "route_id": route.id, "target_adapter_id": route.target_adapter_id, "target_chat_id": route.target_chat_id})
                target_message_id = await adapter.publish_post(route.target_chat_id, post)
                await message_links_repo.create(
                    origin_platform=post.source_platform.value,
                    origin_adapter_id=post.source_adapter_id,
                    origin_chat_id=post.source_chat_id,
                    origin_message_id=post.source_message_id,
                    target_platform=route.target_platform.value,
                    target_adapter_id=route.target_adapter_id,
                    target_chat_id=route.target_chat_id,
                    target_message_id=target_message_id,
                )
                await heartbeat.stop()
                await jobs_repo.mark_succeeded(job["id"], lock_token=job["lock_token"])
                await session.commit()
                logger.info("delivery job succeeded | %s", {"job_id": job["id"], "target_message_id": target_message_id})
                processed += 1
            except Exception as exc:
                await heartbeat.stop()
                logger.exception("delivery job failed | %s", {"job_id": job["id"], "target_platform": job["target_platform"]})
                try:
                    adapter._log_error(f"delivery publish failed: {exc}", code="delivery_publish_failed", job_id=job["id"], route_id=route.id, target_chat_id=route.target_chat_id)
                except Exception:
                    pass
                media_types = [item.type for item in unified_post_from_dict(job["payload"]["post"]).media]
                decision = retry_policy.decide(
                    platform=Platform(job["target_platform"]),
                    media_types=media_types,
                    error=exc,
                    attempts=job["attempts"] + 1,
                    max_attempts=job["max_attempts"],
                )
                if decision.should_retry:
                    logger.warning("delivery job scheduled for retry | %s", {"job_id": job["id"], "error_code": decision.error_code, "delay_seconds": decision.delay_seconds})
                    await jobs_repo.mark_retry(
                        job["id"],
                        lock_token=job["lock_token"],
                        attempts=job["attempts"] + 1,
                        next_attempt_at=retry_policy.next_attempt_at(decision.delay_seconds),
                        last_error=str(exc),
                        error_code=decision.error_code,
                    )
                else:
                    logger.error("delivery job dead-lettered | %s", {"job_id": job["id"], "error_code": decision.error_code})
                    await jobs_repo.mark_dead_letter(
                        job["id"],
                        lock_token=job["lock_token"],
                        attempts=job["attempts"] + 1,
                        last_error=str(exc),
                        error_code=decision.error_code,
                    )
                await session.commit()
                processed += 1
    return processed
