from app.domain.enums import Platform
from app.domain.policies import SyncRule


class InMemoryRulesRepo:
    def __init__(self) -> None:
        self._rules: dict[tuple[Platform, Platform], SyncRule] = {}

    async def upsert(self, rule: SyncRule) -> SyncRule:
        self._rules[(rule.source_platform, rule.target_platform)] = rule
        return rule

    async def get_rule(self, source_platform: Platform, target_platform: Platform) -> SyncRule | None:
        return self._rules.get((source_platform, target_platform))

    async def list_all(self) -> list[SyncRule]:
        return list(self._rules.values())

    async def delete(self, source_platform: Platform, target_platform: Platform) -> bool:
        return self._rules.pop((source_platform, target_platform), None) is not None
