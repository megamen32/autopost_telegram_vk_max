from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost


class MaxWebhookHandler:
    def __init__(self, *, instance_id: str, secret: str | None = None, allowed_source_chat_ids: list[str] | None = None) -> None:
        self.instance_id = instance_id
        self.secret = secret
        self.allowed_source_chat_ids = set(allowed_source_chat_ids or [])

    async def preprocess_webhook(self, payload: dict[str, Any], request: Request | None = None):
        if self.secret and request is not None:
            header_secret = request.headers.get("X-Max-Bot-Api-Secret")
            if header_secret != self.secret:
                raise HTTPException(status_code=401, detail="Invalid MAX webhook secret")
        return None

    def parse_incoming_event(self, payload: dict[str, Any]) -> UnifiedPost | None:
        update_type = payload.get("update_type")
        if update_type != "message_created":
            return None
        message = payload.get("message") or {}
        recipient = message.get("recipient") or {}
        chat_id = recipient.get("chat_id") or recipient.get("user_id")
        message_body = message.get("body") or {}
        message_id = self._extract_message_id(message)
        if chat_id is None or message_id is None:
            return None
        source_chat_id = str(chat_id)
        if self.allowed_source_chat_ids and source_chat_id not in self.allowed_source_chat_ids:
            return None
        link = message.get("link") or {}
        is_repost = bool(link)
        return UnifiedPost(
            source_platform=Platform.MAX,
            source_adapter_id=self.instance_id,
            source_chat_id=source_chat_id,
            source_message_id=str(message_id),
            text=message_body.get("text"),
            media=self._extract_media_items(message_body),
            is_repost=is_repost,
            original_platform=Platform.MAX if is_repost else None,
            original_chat_id=str((link.get("sender") or {}).get("chat_id")) if is_repost and (link.get("sender") or {}).get("chat_id") else None,
            original_message_id=str(link.get("mid")) if is_repost and link.get("mid") is not None else None,
            raw_payload=payload,
        )

    def _extract_message_id(self, message: dict[str, Any]) -> int | str | None:
        for key in ("message_id", "id", "mid"):
            value = message.get(key)
            if value is not None:
                return value
        return None

    def _extract_media_items(self, body: dict[str, Any]) -> list[MediaItem]:
        attachments = body.get("attachments") or []
        items: list[MediaItem] = []
        for attachment in attachments:
            attachment_type = attachment.get("type")
            payload = attachment.get("payload") or {}
            if attachment_type == "image":
                items.append(MediaItem(type=ContentType.IMAGE, file_id=payload.get("token"), url=payload.get("url"), mime_type="image/*", meta={"max_attachment": attachment}))
            elif attachment_type == "video":
                items.append(MediaItem(type=ContentType.VIDEO, file_id=payload.get("token"), url=payload.get("url"), mime_type="video/*", meta={"max_attachment": attachment}))
            elif attachment_type == "audio":
                items.append(MediaItem(type=ContentType.AUDIO, file_id=payload.get("token"), url=payload.get("url"), mime_type="audio/*", meta={"max_attachment": attachment}))
            elif attachment_type == "file":
                items.append(MediaItem(type=ContentType.DOCUMENT, file_id=payload.get("token"), url=payload.get("url"), filename=payload.get("file_name"), size_bytes=payload.get("size"), meta={"max_attachment": attachment}))
        return items
