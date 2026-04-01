from app.adapters.registry import AdapterRegistry
from app.domain.models import UnifiedPost
from app.domain.policies import Route


class DeliveryService:
    def __init__(self, adapter_registry: AdapterRegistry, message_links_repo) -> None:
        self.adapter_registry = adapter_registry
        self.message_links_repo = message_links_repo

    async def deliver(self, route: Route, post: UnifiedPost) -> str:
        adapter = self.adapter_registry.get(route.target_platform)
        target_message_id = await adapter.publish_post(route.target_chat_id, post)

        await self.message_links_repo.create(
            origin_platform=post.source_platform.value,
            origin_chat_id=post.source_chat_id,
            origin_message_id=post.source_message_id,
            target_platform=route.target_platform.value,
            target_chat_id=route.target_chat_id,
            target_message_id=target_message_id,
        )
        return target_message_id
