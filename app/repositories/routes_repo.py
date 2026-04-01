from app.domain.enums import Platform
from app.domain.policies import Route


class InMemoryRoutesRepo:
    def __init__(self) -> None:
        self._routes: dict[str, Route] = {}

    async def upsert(self, route: Route) -> Route:
        self._routes[route.id] = route
        return route

    async def get(self, route_id: str) -> Route | None:
        return self._routes.get(route_id)

    async def list_all(self) -> list[Route]:
        return list(self._routes.values())

    async def delete(self, route_id: str) -> bool:
        return self._routes.pop(route_id, None) is not None

    async def list_enabled_for_source(self, source_platform: Platform, source_chat_id: str) -> list[Route]:
        return [
            route
            for route in self._routes.values()
            if route.enabled and route.source_platform == source_platform and route.source_chat_id == source_chat_id
        ]
