class DedupService:
    def __init__(self, processed_events_repo) -> None:
        self.processed_events_repo = processed_events_repo

    async def is_processed(self, source_platform: str, source_chat_id: str, source_message_id: str) -> bool:
        return await self.processed_events_repo.exists(
            source_platform=source_platform,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
        )

    async def mark_processed(
        self,
        source_platform: str,
        source_chat_id: str,
        source_message_id: str,
        content_hash: str,
    ) -> None:
        await self.processed_events_repo.create(
            source_platform=source_platform,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            content_hash=content_hash,
        )
