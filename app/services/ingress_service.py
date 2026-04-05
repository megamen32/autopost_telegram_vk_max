from app.adapters.registry import AdapterRegistry


class IngressService:
    def __init__(self, adapter_registry: AdapterRegistry, sync_service) -> None:
        self.adapter_registry = adapter_registry
        self.sync_service = sync_service

    async def handle_event(self, adapter_instance_id: str, payload: dict) -> None:
        adapter = self.adapter_registry.get_by_instance(adapter_instance_id)
        post = await adapter.parse_incoming_event(payload)
        if post is None:
            return
        await self.sync_service.handle_post(post)
