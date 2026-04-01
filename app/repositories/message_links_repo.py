class InMemoryMessageLinksRepo:
    def __init__(self) -> None:
        self._links: list[dict] = []

    async def create(
        self,
        origin_platform: str,
        origin_chat_id: str,
        origin_message_id: str,
        target_platform: str,
        target_chat_id: str,
        target_message_id: str,
    ) -> dict:
        link = {
            "origin_platform": origin_platform,
            "origin_chat_id": origin_chat_id,
            "origin_message_id": origin_message_id,
            "target_platform": target_platform,
            "target_chat_id": target_chat_id,
            "target_message_id": target_message_id,
        }
        self._links.append(link)
        return link

    async def list_all(self) -> list[dict]:
        return list(self._links)
