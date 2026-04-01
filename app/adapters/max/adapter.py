from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import HTTPException, Request

from app.adapters.base import BaseAdapter
from app.adapters.max.client import MaxApiError, MaxClient
from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost

logger = logging.getLogger(__name__)


class MaxAdapter(BaseAdapter):
    platform = Platform.MAX

    def __init__(
        self,
        *,
        token: str | None = None,
        webhook_url: str | None = None,
        secret: str | None = None,
        update_types: list[str] | None = None,
        receive_updates: bool = True,
        allowed_source_chat_ids: list[str] | None = None,
    ) -> None:
        self.token = token
        self.webhook_url = webhook_url
        self.secret = secret
        self.update_types = update_types or ["message_created"]
        self.receive_updates = receive_updates
        self.allowed_source_chat_ids = set(allowed_source_chat_ids or [])
        self._client: MaxClient | None = None
        self._on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    async def startup(self, on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None) -> None:
        self._on_post = on_post
        if not self.enabled:
            logger.info("MaxAdapter disabled: no MAX token configured")
            return

        if self.receive_updates and self.webhook_url:
            try:
                client = self._get_client()
                await client.subscribe_webhook(
                    url=self.webhook_url,
                    update_types=self.update_types,
                    secret=self.secret,
                )
                logger.info("MAX webhook subscription registered")
            except Exception:
                logger.exception("Failed to register MAX webhook subscription")

    async def preprocess_webhook(self, payload: dict, request: Request | None = None):
        if self.secret and request is not None:
            header_secret = request.headers.get("X-Max-Bot-Api-Secret")
            if header_secret != self.secret:
                raise HTTPException(status_code=401, detail="Invalid MAX webhook secret")
        return None

    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
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
            source_platform=self.platform,
            source_chat_id=source_chat_id,
            source_message_id=str(message_id),
            text=message_body.get("text"),
            media=self._extract_media_items(message_body),
            is_repost=is_repost,
            original_platform=self.platform if is_repost else None,
            original_chat_id=str((link.get("sender") or {}).get("chat_id")) if is_repost and (link.get("sender") or {}).get("chat_id") else None,
            original_message_id=str(link.get("mid")) if is_repost and link.get("mid") is not None else None,
            raw_payload=payload,
        )

    async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
        if not self.enabled:
            return f"max-dry-run-{chat_id}-{post.source_message_id}"

        client = self._get_client()
        attachments = await self._prepare_attachments(client=client, media=post.media)
        body: dict[str, Any] = {
            "text": post.text,
            "attachments": attachments or None,
            "notify": True,
        }
        if body["text"]:
            body["format"] = "markdown"
        try:
            response = await client.send_message(chat_id=int(chat_id), body=body)
        except MaxApiError as exc:
            if attachments:
                logger.warning("MAX message send failed with attachments, retrying without attachments: %s", exc)
                fallback_text = post.text or ""
                fallback_links = [item.url for item in post.media if item.url]
                if fallback_links:
                    fallback_text = (fallback_text + "\n\n" if fallback_text else "") + "\n".join(fallback_links)
                response = await client.send_message(chat_id=int(chat_id), body={"text": fallback_text or "(empty)", "format": "markdown"})
            else:
                raise

        message = response.get("message") or response
        message_id = self._extract_message_id(message)
        return str(message_id) if message_id is not None else f"max-{chat_id}-unknown"

    async def delete_post(self, chat_id: str, message_id: str) -> None:
        if not self.enabled:
            return None
        client = self._get_client()
        await client.delete_message(int(message_id))
        return None

    async def edit_post(self, chat_id: str, message_id: str, post: UnifiedPost) -> None:
        if not self.enabled:
            return None
        client = self._get_client()
        attachments = await self._prepare_attachments(client=client, media=post.media)
        body: dict[str, Any] = {"text": post.text, "attachments": attachments or None}
        if body["text"]:
            body["format"] = "markdown"
        await client.edit_message(int(message_id), body)
        return None

    async def supports_feature(self, feature: str) -> bool:
        supported = {"text", "image", "video", "audio", "document", "repost"}
        return feature in supported

    def _get_client(self) -> MaxClient:
        if self._client is None:
            if not self.token:
                raise MaxApiError("MaxAdapter is not configured")
            self._client = MaxClient(token=self.token)
        return self._client

    def _extract_message_id(self, message: dict[str, Any]) -> int | str | None:
        for key in ("message_id", "mid", "id"):
            if message.get(key) is not None:
                return message[key]
        return None

    def _extract_media_items(self, body: dict[str, Any]) -> list[MediaItem]:
        items: list[MediaItem] = []
        for attachment in body.get("attachments") or []:
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

    async def _prepare_attachments(self, *, client: MaxClient, media: list[MediaItem]) -> list[dict[str, Any]]:
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

            content = await client.download_bytes(location)
            filename = item.filename or self._guess_filename(location, default=self._default_filename(upload_type))
            attachment = await client.upload_attachment(
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
