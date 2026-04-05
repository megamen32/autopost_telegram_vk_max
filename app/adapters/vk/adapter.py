from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Any, Awaitable, Callable

from fastapi import HTTPException

from app.adapters.base import BaseAdapter
from app.adapters.common import parse_media_items
from app.adapters.vk.client import VkClient
from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost

logger = logging.getLogger(__name__)
_ATTACHMENT_RE = re.compile(r"^(photo|video|audio|doc)-?\d+_\d+(?:_[A-Za-z0-9]+)?$")


class VkAdapter(BaseAdapter):
    platform = Platform.VK

    def __init__(
        self,
        *,
        instance_id: str | None = None,
        token: str | None = None,
        group_id: int | None = None,
        api_version: str = "5.199",
        confirmation_token: str | None = None,
        secret: str | None = None,
        receive_updates: bool = True,
        receive_mode: str = "long_poll",
        allowed_source_chat_ids: list[str] | None = None,
        long_poll_wait_seconds: int = 25,
    ) -> None:
        super().__init__(instance_id=instance_id)
        self.token = token
        self.group_id = group_id
        self.api_version = api_version
        self.confirmation_token = confirmation_token
        self.secret = secret
        self.receive_updates = receive_updates
        self.receive_mode = receive_mode or "long_poll"
        self.long_poll_wait_seconds = long_poll_wait_seconds
        self.allowed_source_chat_ids = set(allowed_source_chat_ids or [])
        self._client: VkClient | None = None
        self._on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None
        self._polling_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.group_id)

    def _get_client(self) -> VkClient:
        if self._client is None:
            if not self.enabled:
                raise RuntimeError("VkAdapter is not configured")
            self._client = VkClient(self.token, api_version=self.api_version)
        return self._client

    async def startup(self, on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None) -> None:
        self._on_post = on_post
        self._stop_event.clear()
        if not self.enabled:
            logger.info("VkAdapter disabled: no VK credentials configured")
            return
        if self.receive_updates and self.receive_mode == "long_poll" and on_post is not None:
            self._polling_task = asyncio.create_task(self._run_long_poll_loop(), name=f"vk-long-poll-{self.instance_id}")
            self._set_status("running", connected=True)
            self._log_info("vk long poll started")

    async def shutdown(self) -> None:
        self._stop_event.set()
        if self._polling_task is not None:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
        self._mark_shutdown()

    async def preprocess_webhook(self, payload: dict) -> dict[str, Any] | str | None:
        event_type = payload.get("type")
        if event_type == "confirmation":
            return self.confirmation_token or "ok"
        if self.secret and payload.get("secret") != self.secret:
            raise HTTPException(status_code=403, detail="Invalid VK callback secret")
        if event_type in {"message_new", "wall_post_new"}:
            return None
        return "ok"

    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
        event_type = payload.get("type")
        if event_type == "message_new":
            return self._parse_message_new(payload)
        if event_type == "wall_post_new":
            return self._parse_wall_post_new(payload)

        chat_id = payload.get("chat_id")
        message_id = payload.get("message_id")
        if not chat_id or not message_id:
            return None

        return UnifiedPost(
            source_platform=self.platform,
            source_adapter_id=self.instance_id,
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
        if not self.enabled:
            logger.info("VkAdapter disabled: returning dry-run id")
            return f"vk-dry-run-{chat_id}-{uuid.uuid4().hex[:12]}"

        owner_id = self._normalize_owner_id(chat_id)
        client = self._get_client()

        attachments: list[str] = []
        append_links_to_text: list[str] = []

        for item in post.media:
            attachment = await self._prepare_attachment(client=client, owner_id=owner_id, item=item)
            if attachment is None:
                fallback_link = item.url or item.file_id
                if fallback_link and fallback_link.startswith(("http://", "https://")):
                    append_links_to_text.append(fallback_link)
                continue
            attachments.append(attachment)

        message_text = post.text or ""
        if append_links_to_text:
            links_block = "\n".join(append_links_to_text)
            message_text = f"{message_text}\n{links_block}".strip()

        response = await client.call_method(
            "wall.post",
            {
                "owner_id": owner_id,
                "from_group": 1,
                "message": message_text,
                "attachments": ",".join(attachments) if attachments else None,
            },
        )
        return str(response["post_id"])

    async def delete_post(self, chat_id: str, message_id: str) -> None:
        if not self.enabled:
            return None
        owner_id = self._normalize_owner_id(chat_id)
        client = self._get_client()
        await client.call_method(
            "wall.delete",
            {
                "owner_id": owner_id,
                "post_id": int(message_id),
            },
        )

    async def edit_post(self, chat_id: str, message_id: str, post: UnifiedPost) -> None:
        if not self.enabled:
            return None
        owner_id = self._normalize_owner_id(chat_id)
        client = self._get_client()
        await client.call_method(
            "wall.edit",
            {
                "owner_id": owner_id,
                "post_id": int(message_id),
                "message": post.text or "",
            },
        )

    async def supports_feature(self, feature: str) -> bool:
        supported = {"text", "image", "video", "audio", "document", "repost", "long_poll", "webhook"}
        return feature in supported

    async def _run_long_poll_loop(self) -> None:
        if self._on_post is None:
            return
        client = self._get_client()
        ts: str | int | None = None
        key: str | None = None
        server: str | None = None
        while not self._stop_event.is_set():
            try:
                if not all([ts, key, server]):
                    server_info = await client.get_bot_long_poll_server(self.group_id)
                    key = server_info["key"]
                    server = server_info["server"]
                    ts = server_info["ts"]
                response = await client.long_poll_once(server=server, key=key, ts=ts, wait=self.long_poll_wait_seconds)
                failed = response.get("failed")
                if failed:
                    server_info = await client.get_bot_long_poll_server(self.group_id)
                    key = server_info["key"]
                    server = server_info["server"]
                    ts = server_info["ts"]
                    continue
                ts = response.get("ts", ts)
                for update in response.get("updates") or []:
                    post = await self.parse_incoming_event(update)
                    if post is not None:
                        await self._on_post(post)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._log_error(f"vk long poll loop failed: {exc}", code="vk_long_poll_failed")
                await asyncio.sleep(3)

    def _parse_message_new(self, payload: dict) -> UnifiedPost | None:
        obj = payload.get("object") or {}
        message = obj.get("message") or obj
        peer_id = message.get("peer_id")
        message_id = message.get("id") or message.get("conversation_message_id")
        if peer_id is None or message_id is None:
            return None

        source_chat_id = str(peer_id)
        if self.allowed_source_chat_ids and source_chat_id not in self.allowed_source_chat_ids:
            self._mark_event_ignored("chat_not_allowed", chat_id=source_chat_id)
            return None

        attachments = message.get("attachments") or []
        return UnifiedPost(
            source_platform=self.platform,
            source_adapter_id=self.instance_id,
            source_chat_id=source_chat_id,
            source_message_id=str(message_id),
            text=message.get("text") or None,
            media=self._parse_vk_attachments(attachments),
            is_repost=bool(message.get("fwd_messages") or message.get("reply_message")),
            raw_payload=payload,
        )

    def _parse_wall_post_new(self, payload: dict) -> UnifiedPost | None:
        post = payload.get("object") or {}
        owner_id = post.get("owner_id")
        post_id = post.get("id")
        if owner_id is None or post_id is None:
            return None

        source_chat_id = str(owner_id)
        if self.allowed_source_chat_ids and source_chat_id not in self.allowed_source_chat_ids:
            self._mark_event_ignored("chat_not_allowed", chat_id=source_chat_id)
            return None

        attachments = post.get("attachments") or []
        return UnifiedPost(
            source_platform=self.platform,
            source_adapter_id=self.instance_id,
            source_chat_id=source_chat_id,
            source_message_id=str(post_id),
            text=post.get("text") or None,
            media=self._parse_vk_attachments(attachments),
            is_repost=bool(post.get("copy_history")),
            original_platform=self.platform if post.get("copy_history") else None,
            raw_payload=payload,
        )

    def _parse_vk_attachments(self, attachments: list[dict]) -> list[MediaItem]:
        items: list[MediaItem] = []
        for attachment in attachments:
            attachment_type = attachment.get("type")
            payload = attachment.get(attachment_type or "", {})
            if not attachment_type or not payload:
                continue

            owner_id = payload.get("owner_id")
            media_id = payload.get("id")
            access_key = payload.get("access_key")
            attachment_ref = None
            if owner_id is not None and media_id is not None:
                attachment_ref = f"{attachment_type}{owner_id}_{media_id}"
                if access_key:
                    attachment_ref = f"{attachment_ref}_{access_key}"

            if attachment_type == "photo":
                best_size = self._pick_largest_photo(payload.get("sizes") or [])
                items.append(MediaItem(type=ContentType.IMAGE, file_id=attachment_ref, url=best_size.get("url") if best_size else None, mime_type="image/jpeg", meta={"vk_attachment": attachment_ref}))
            elif attachment_type == "video":
                items.append(MediaItem(type=ContentType.VIDEO, file_id=attachment_ref, url=payload.get("player"), mime_type="video/mp4", meta={"vk_attachment": attachment_ref}))
            elif attachment_type == "audio":
                items.append(MediaItem(type=ContentType.AUDIO, file_id=attachment_ref, mime_type="audio/mpeg", meta={"vk_attachment": attachment_ref}))
            elif attachment_type == "doc":
                items.append(MediaItem(type=ContentType.DOCUMENT, file_id=attachment_ref, url=payload.get("url"), mime_type=payload.get("ext"), filename=payload.get("title"), size_bytes=payload.get("size"), meta={"vk_attachment": attachment_ref}))
        return items

    @staticmethod
    def _pick_largest_photo(sizes: list[dict]) -> dict | None:
        if not sizes:
            return None
        return max(sizes, key=lambda item: item.get("width", 0) * item.get("height", 0))

    @staticmethod
    def _normalize_owner_id(chat_id: str | int) -> int:
        value = int(chat_id)
        return value if value < 0 else -value

    async def _prepare_attachment(self, *, client: VkClient, owner_id: int, item: MediaItem) -> str | None:
        vk_attachment = item.meta.get("vk_attachment") if item.meta else None
        if isinstance(vk_attachment, str) and _ATTACHMENT_RE.match(vk_attachment):
            return vk_attachment

        if item.type == ContentType.IMAGE and item.url:
            upload_server = await client.call_method(
                "photos.getWallUploadServer",
                {"group_id": abs(owner_id)},
            )
            content = await client.download_bytes(item.url)
            upload_result = await client.upload_file(
                upload_server["upload_url"],
                form_field="photo",
                filename=item.filename or "image.jpg",
                content=content,
                content_type=item.mime_type,
            )
            saved = await client.call_method(
                "photos.saveWallPhoto",
                {
                    "group_id": abs(owner_id),
                    "photo": upload_result["photo"],
                    "server": upload_result["server"],
                    "hash": upload_result["hash"],
                },
            )
            photo = saved[0]
            return f"photo{photo['owner_id']}_{photo['id']}"

        if item.type == ContentType.DOCUMENT and item.url:
            upload_server = await client.call_method(
                "docs.getWallUploadServer",
                {"group_id": abs(owner_id)},
            )
            content = await client.download_bytes(item.url)
            upload_result = await client.upload_file(
                upload_server["upload_url"],
                form_field="file",
                filename=item.filename or "document.bin",
                content=content,
                content_type=item.mime_type,
            )
            saved = await client.call_method(
                "docs.save",
                {"file": upload_result["file"]},
            )
            doc = saved["doc"] if isinstance(saved, dict) else saved[0]
            return f"doc{doc['owner_id']}_{doc['id']}"

        if item.type == ContentType.VIDEO:
            if item.file_id and _ATTACHMENT_RE.match(str(item.file_id)):
                return str(item.file_id)
            if item.url:
                return None

        if item.type == ContentType.AUDIO:
            if item.file_id and _ATTACHMENT_RE.match(str(item.file_id)):
                return str(item.file_id)
            return None

        return None
