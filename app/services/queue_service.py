from __future__ import annotations

from app.domain.models import UnifiedPost
from app.domain.policies import Route
from app.repositories.delivery_jobs_repo import DeliveryJobsRepo
from app.utils.serialization import route_to_dict, unified_post_to_dict


class QueueService:
    def __init__(self, delivery_jobs_repo: DeliveryJobsRepo, *, max_attempts: int) -> None:
        self.delivery_jobs_repo = delivery_jobs_repo
        self.max_attempts = max_attempts

    async def enqueue_delivery(self, *, route: Route, post: UnifiedPost) -> dict:
        payload = {
            "route": route_to_dict(route),
            "post": unified_post_to_dict(post),
        }
        return await self.delivery_jobs_repo.enqueue(
            route_id=route.id,
            target_platform=route.target_platform.value,
            target_chat_id=route.target_chat_id,
            origin_platform=post.source_platform.value,
            origin_chat_id=post.source_chat_id,
            origin_message_id=post.source_message_id,
            payload=payload,
            max_attempts=self.max_attempts,
        )
