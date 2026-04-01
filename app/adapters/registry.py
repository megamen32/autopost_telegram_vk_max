from app.adapters.base import BaseAdapter
from app.domain.enums import Platform
from app.domain.errors import AdapterNotFoundError


class AdapterRegistry:
    def __init__(self, adapters: dict[Platform, BaseAdapter]) -> None:
        self._adapters = adapters

    def get(self, platform: Platform) -> BaseAdapter:
        adapter = self._adapters.get(platform)
        if adapter is None:
            raise AdapterNotFoundError(f"Adapter for platform={platform.value} not found")
        return adapter

    def list_platforms(self) -> list[str]:
        return [platform.value for platform in self._adapters]
