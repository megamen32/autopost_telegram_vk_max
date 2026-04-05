from app.adapters.base import BaseAdapter
from app.domain.enums import Platform
from app.domain.errors import AdapterNotFoundError


class AdapterRegistry:
    def __init__(self, adapters: dict[str, BaseAdapter]) -> None:
        self._adapters = adapters

    def get_by_instance(self, adapter_instance_id: str) -> BaseAdapter:
        adapter = self._adapters.get(adapter_instance_id)
        if adapter is None:
            raise AdapterNotFoundError(f"Adapter instance={adapter_instance_id} not found")
        return adapter

    def get(self, platform: Platform) -> BaseAdapter:
        for adapter in self._adapters.values():
            if adapter.platform == platform:
                return adapter
        raise AdapterNotFoundError(f"Adapter for platform={platform.value} not found")

    def list_platforms(self) -> list[str]:
        return sorted({adapter.platform.value for adapter in self._adapters.values()})

    def list_instances(self) -> list[dict[str, str]]:
        return [
            {
                "instance_id": adapter_id,
                "platform": adapter.platform.value,
                "class": adapter.__class__.__name__,
            }
            for adapter_id, adapter in sorted(self._adapters.items())
        ]
