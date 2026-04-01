class InMemoryProcessedEventsRepo:
    def __init__(self) -> None:
        self._events: dict[tuple[str, str, str], dict] = {}

    async def exists(self, source_platform: str, source_chat_id: str, source_message_id: str) -> bool:
        return (source_platform, source_chat_id, source_message_id) in self._events

    async def create(self, source_platform: str, source_chat_id: str, source_message_id: str, content_hash: str) -> None:
        self._events[(source_platform, source_chat_id, source_message_id)] = {
            "source_platform": source_platform,
            "source_chat_id": source_chat_id,
            "source_message_id": source_message_id,
            "content_hash": content_hash,
        }

    async def list_all(self) -> list[dict]:
        return list(self._events.values())
