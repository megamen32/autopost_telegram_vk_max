from app.adapters.registry import AdapterRegistry
from app.domain.enums import Platform


class IngressService:
    def __init__(self, adapter_registry: AdapterRegistry, sync_service) -> None:
        self.adapter_registry = adapter_registry
        self.sync_service = sync_service

    async def handle_event(self, platform: Platform, payload: dict) -> None:
        adapter = self.adapter_registry.get(platform)
        post = await adapter.parse_incoming_event(payload)
        if post is None:
            return
        await self.sync_service.handle_post(post)
