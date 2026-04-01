class InMemoryPlatformAccountsRepo:
    def __init__(self) -> None:
        self._accounts: dict[str, dict] = {}

    async def set(self, platform: str, data: dict) -> None:
        self._accounts[platform] = data

    async def get(self, platform: str) -> dict | None:
        return self._accounts.get(platform)
