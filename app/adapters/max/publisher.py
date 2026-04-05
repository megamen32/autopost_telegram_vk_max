from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.adapters.max.client import MaxApiError, MaxClient
from app.domain.enums import ContentType
from app.domain.models import MediaItem, UnifiedPost

logger = logging.getLogger(__name__)


class MaxPublisher:
    def __init__(self, client: MaxClient) -> None:
        self.client = client

    async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
        attachments = await self._prepare_attachments(post.media)
        body: dict[str, Any] = {
            "text": post.text,
            "attachments": attachments or None,
            "notify": True,
        }
        if body["text"]:
            body["format"] = "markdown"
        try:
            response = await self.client.send_message(chat_id=int(chat_id), body=body)
        except MaxApiError as exc:
            if attachments:
                logger.warning("MAX message send failed with attachments, retrying without attachments: %s", exc)
                fallback_text = post.text or ""
                fallback_links = [item.url for item in post.media if item.url]
                if fallback_links:
                    fallback_text = (fallback_text + "\n\n" if fallback_text else "") + "\n".join(fallback_links)
                response = await self.client.send_message(chat_id=int(chat_id), body={"text": fallback_text or "(empty)", "format": "markdown"})
            else:
                raise
        message = response.get("message") or response
        message_id = message.get("message_id") or message.get("id") or message.get("mid")
        return str(message_id) if message_id is not None else f"max-{chat_id}-unknown"

    async def edit_post(self, chat_id: str, message_id: str, post: UnifiedPost) -> None:
        body: dict[str, Any] = {"text": post.text, "format": "markdown" if post.text else None}
        await self.client.edit_message(int(message_id), body)

    async def delete_post(self, chat_id: str, message_id: str) -> None:
        await self.client.delete_message(int(message_id))

    async def _prepare_attachments(self, media: list[MediaItem]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in media:
            existing = item.meta.get("max_attachment") if item.meta else None
            if isinstance(existing, dict) and existing.get("type") and existing.get("payload"):
                result.append(existing)
                continue
            upload_type = self._to_max_upload_type(item.type)
            if upload_type is None:
                continue
            location = item.file_id or item.url
            if not location:
                continue
            content = await self.client.download_bytes(location)
            filename = item.filename or self._guess_filename(location, default=self._default_filename(upload_type))
            attachment = await self.client.upload_attachment(
                upload_type=upload_type,
                filename=filename,
                content=content,
                content_type=item.mime_type,
            )
            result.append(attachment)
        return result

    def _to_max_upload_type(self, content_type: ContentType) -> str | None:
        if content_type == ContentType.IMAGE:
            return "image"
        if content_type == ContentType.VIDEO:
            return "video"
        if content_type == ContentType.AUDIO:
            return "audio"
        if content_type == ContentType.DOCUMENT:
            return "file"
        return None

    def _guess_filename(self, location: str, default: str) -> str:
        if "/" in location:
            tail = location.rsplit("/", 1)[-1]
            if tail:
                return tail.split("?", 1)[0]
        return Path(location).name or default

    def _default_filename(self, upload_type: str) -> str:
        mapping = {
            "image": "image.jpg",
            "video": "video.mp4",
            "audio": "audio.mp3",
            "file": "file.bin",
        }
        return mapping.get(upload_type, "file.bin")
