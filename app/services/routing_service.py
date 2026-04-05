from app.domain.models import UnifiedPost
from app.domain.policies import Route, SyncRule


class RoutingService:
    def __init__(self, routes_repo, rules_repo=None) -> None:
        self.routes_repo = routes_repo
        self.rules_repo = rules_repo

    async def resolve_destinations(self, post: UnifiedPost) -> list[tuple[Route, SyncRule]]:
        routes = await self.routes_repo.list_enabled_for_source(
            source_adapter_id=post.source_adapter_id,
            source_chat_id=post.source_chat_id,
        )

        result: list[tuple[Route, SyncRule]] = []
        for route in routes:
            rule = route.to_sync_rule()
            if rule is None or not rule.enabled:
                continue
            result.append((route, rule))
        return result
