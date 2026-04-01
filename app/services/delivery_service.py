from app.domain.models import UnifiedPost
from app.domain.policies import Route
from app.services.queue_service import QueueService


class DeliveryService:
    def __init__(self, queue_service: QueueService) -> None:
        self.queue_service = queue_service

    async def deliver(self, route: Route, post: UnifiedPost) -> str:
        job = await self.queue_service.enqueue_delivery(route=route, post=post)
        return str(job["id"])
