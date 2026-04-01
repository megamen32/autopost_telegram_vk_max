import uuid

from app.adapters.base import BaseAdapter
from app.adapters.common import parse_media_items
from app.domain.enums import Platform
from app.domain.models import UnifiedPost


class MaxAdapter(BaseAdapter):
    platform = Platform.MAX

    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
        chat_id = payload.get("chat_id")
        message_id = payload.get("message_id")
        if not chat_id or not message_id:
            return None

        return UnifiedPost(
            source_platform=self.platform,
            source_chat_id=str(chat_id),
            source_message_id=str(message_id),
            text=payload.get("text"),
            media=parse_media_items(payload.get("media")),
            is_repost=bool(payload.get("is_repost", False)),
            original_platform=Platform(payload["original_platform"]) if payload.get("original_platform") else None,
            original_chat_id=payload.get("original_chat_id"),
            original_message_id=payload.get("original_message_id"),
            raw_payload=payload,
        )

    async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
        return f"max-{chat_id}-{uuid.uuid4().hex[:12]}"

    async def delete_post(self, chat_id: str, message_id: str) -> None:
        return None

    async def edit_post(self, chat_id: str, message_id: str, post: UnifiedPost) -> None:
        return None

    async def supports_feature(self, feature: str) -> bool:
        supported = {"text", "image", "video", "audio", "document", "repost"}
        return feature in supported
