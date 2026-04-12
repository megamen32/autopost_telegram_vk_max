from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Awaitable, Callable

from app.adapters.base import BaseAdapter
from app.adapters.common import parse_media_items
from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost

logger = logging.getLogger(__name__)


class TelegramAdapter(BaseAdapter):
    platform = Platform.TELEGRAM

    def __init__(
        self,
        *,
        instance_id: str | None = None,
        api_id: int | None = None,
        api_hash: str | None = None,
        string_session: str | None = None,
        bot_token: str | None = None,
        session_name: str = "autopost_sync",
        receive_updates: bool = True,
        sequential_updates: bool = False,
        allowed_source_chat_ids: list[str] | None = None,
        check_all_chats: bool = False,
        log_level: str = "INFO",
    ) -> None:
        super().__init__(instance_id=instance_id, log_level=log_level)
        self.api_id = api_id
        self.api_hash = api_hash
        self.string_session = string_session
        self.bot_token = bot_token
        self.session_name = session_name
        self.receive_updates = receive_updates
        self.sequential_updates = sequential_updates
        self.allowed_source_chat_ids = set(allowed_source_chat_ids or [])
        self.check_all_chats = check_all_chats

        self._client = None
        self._on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None
        self._started = False
        self._disconnect_task: asyncio.Task | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_id and self.api_hash and (self.string_session or self.bot_token))

    async def startup(self, on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None) -> None:
        self._on_post = on_post
        self._mark_startup()
        if not self.enabled:
            self._log_warning("telegram disabled: missing api_id/api_hash and bot_token|string_session")
            self._set_status("disabled", connected=False)
            return

        try:
            client = await self._get_client()
            me = await client.get_me()
            if self.receive_updates and on_post is not None:
                events = self._telethon_events_module()
                client.add_event_handler(self._handle_new_message_event, events.NewMessage(incoming=True))
            self._started = True
            self._set_status("running", connected=True)
            self._log_info(f"telegram started in telethon mode as {getattr(me, 'username', None) or getattr(me, 'id', 'unknown')}")
        except Exception as exc:
            self._log_error(f"telegram startup failed: {exc}", code="telegram_startup_failed")
            self._set_status("startup_failed", connected=False)
            raise

    async def shutdown(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
        if self._disconnect_task is not None:
            self._disconnect_task.cancel()
        self._started = False
        self._mark_shutdown()

    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
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
        client = await self._get_client(required=True)
        target = self._normalize_target_entity(chat_id)

        media_items = list(post.media)
        files: list[str] = []
        for item in media_items:
            path = self._resolve_media_source(item)
            if path is not None:
                files.append(path)
            else:
                self._log_warning(
                    "telegram publish skipped unresolved media item",
                    media_type=item.type.value,
                    file_id=item.file_id,
                    url=item.url,
                )

        self._log_info(f"telegram publish to chat_id={chat_id} normalized_target={target!r}")
        if files:
            result = await client.send_file(
                entity=target,
                file=files if len(files) > 1 else files[0],
                caption=post.text or "",
                force_document=all(item.type == ContentType.DOCUMENT for item in media_items),
                supports_streaming=any(item.type == ContentType.VIDEO for item in media_items),
            )
        else:
            result = await client.send_message(entity=target, message=post.text or "")

        if isinstance(result, list):
            result_id = str(result[0].id)
        else:
            result_id = str(result.id)
        self._mark_publish(chat_id=chat_id, message_id=result_id)
        return result_id

    async def delete_post(self, chat_id: str, message_id: str) -> None:
        client = await self._get_client(required=True)
        target = self._normalize_target_entity(chat_id)
        await client.delete_messages(entity=target, message_ids=[int(message_id)])

    async def edit_post(self, chat_id: str, message_id: str, post: UnifiedPost) -> None:
        client = await self._get_client(required=True)
        target = self._normalize_target_entity(chat_id)
        await client.edit_message(entity=target, message=int(message_id), text=post.text or "")

    async def resolve_chat_reference(self, value: str | int) -> str:
        normalized = self._normalize_target_entity(value)
        if isinstance(normalized, int):
            self._log_info("telegram resolve numeric chat reference", raw=value, canonical=str(normalized))
            return str(normalized)

        ref = self._extract_public_reference(str(normalized))
        if ref is None:
            self._log_warning("telegram resolve fallback: unsupported reference format", raw=value)
            return str(normalized)

        client = await self._get_client(required=True)
        try:
            entity = await client.get_entity(ref)
            entity_id = self._extract_chat_id(entity) or self._extract_peer_id(getattr(entity, "peer_id", None))
            if entity_id is None:
                raise RuntimeError(f"Could not resolve Telegram reference: {value}")
            self._log_info("telegram resolve success", raw=value, canonical=str(entity_id))
            return str(entity_id)
        except Exception as exc:
            self._log_warning("telegram resolve failed", raw=value, reason=str(exc))
            raise

    def _extract_public_reference(self, value: str) -> str | None:
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.lstrip("-").isdigit():
            return None
        if stripped.startswith("@"):
            return stripped[1:]

        match = re.match(r"https?://t\.me/([A-Za-z0-9_]+)/?$", stripped)
        if match:
            return match.group(1)

        match = re.match(r"https?://telegram\.me/([A-Za-z0-9_]+)/?$", stripped)
        if match:
            return match.group(1)

        if re.fullmatch(r"[A-Za-z0-9_]{5,}", stripped):
            return stripped
        return None

    def _normalize_target_entity(self, value: str | int):
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.lstrip("-").isdigit():
                return int(stripped)
            public_ref = self._extract_public_reference(stripped)
            if public_ref is not None:
                return public_ref
            return stripped
        return value

    async def supports_feature(self, feature: str) -> bool:
        supported = {"text", "image", "video", "audio", "document", "repost"}
        return feature in supported

    def _resolve_media_source(self, item: MediaItem) -> str | None:
        for candidate in (item.url, item.file_id):
            if candidate is None:
                continue
            value = str(candidate).strip()
            if not value:
                continue
            if value.startswith(("http://", "https://")):
                return value
            if Path(value).exists():
                return value
        return None

    async def _handle_new_message_event(self, event) -> None:
        if self._on_post is None:
            self._mark_event_ignored("no_on_post_handler")
            return

        post = await self._message_to_unified_post(event.message)
        if post is None:
            self._mark_event_ignored("message_to_post_returned_none")
            return

        self._mark_event_received(chat_id=post.source_chat_id, message_id=post.source_message_id)
        self._log_info(f"telegram incoming chat_id={post.source_chat_id} message_id={post.source_message_id}")
        if self.allowed_source_chat_ids and post.source_chat_id not in self.allowed_source_chat_ids:
            self._mark_event_ignored("chat_not_allowed", chat_id=post.source_chat_id)
            return

        try:
            await self._on_post(post)
            self._log_info(f"telegram post handed to sync pipeline route_source={post.source_chat_id}")
        except Exception as exc:
            self._log_error(f"telegram on_post failed: {exc}", code="telegram_on_post_failed", chat_id=post.source_chat_id)
            raise

    async def _message_to_unified_post(self, message) -> UnifiedPost | None:
        chat = await message.get_chat()
        source_chat_id = self._extract_chat_id(chat)
        if source_chat_id is None:
            return None

        media = await self._extract_media_items(message)
        original_platform = None
        original_chat_id = None
        original_message_id = None
        is_repost = bool(getattr(message, "fwd_from", None))
        if is_repost:
            original_platform = Platform.TELEGRAM
            fwd_from = getattr(message, "fwd_from", None)
            saved_from_peer = getattr(fwd_from, "saved_from_peer", None) if fwd_from else None
            saved_from_msg_id = getattr(fwd_from, "saved_from_msg_id", None) if fwd_from else None
            original_chat_id = str(self._extract_peer_id(saved_from_peer)) if saved_from_peer else None
            original_message_id = str(saved_from_msg_id) if saved_from_msg_id else None

        return UnifiedPost(
            source_platform=self.platform,
            source_adapter_id=self.instance_id,
            source_chat_id=source_chat_id,
            source_message_id=str(message.id),
            text=message.message,
            media=media,
            is_repost=is_repost,
            original_platform=original_platform,
            original_chat_id=original_chat_id,
            original_message_id=original_message_id,
            raw_payload={"telethon": True},
        )

    async def _extract_media_items(self, message) -> list[MediaItem]:
        media: list[MediaItem] = []
        if not getattr(message, "media", None):
            return media

        mime_type = getattr(getattr(message, "file", None), "mime_type", None)
        size_bytes = getattr(getattr(message, "file", None), "size", None)
        filename = getattr(getattr(message, "file", None), "name", None)

        item_type = self._detect_media_type(message, mime_type)
        file_reference = await self._build_message_permalink(message)
        downloaded_path = await self._download_media_to_tempfile(message, filename=filename, mime_type=mime_type)
        media.append(
            MediaItem(
                type=item_type,
                file_id=file_reference,
                url=downloaded_path,
                mime_type=mime_type,
                filename=filename or (os.path.basename(downloaded_path) if downloaded_path else None),
                size_bytes=size_bytes,
                meta={"telethon_message_id": message.id},
            )
        )
        return media


    async def _download_media_to_tempfile(self, message, *, filename: str | None, mime_type: str | None) -> str | None:
        client = await self._get_client(required=True)
        suffix = ""
        if filename and "." in filename:
            suffix = Path(filename).suffix
        elif mime_type == "image/jpeg":
            suffix = ".jpg"
        elif mime_type == "image/png":
            suffix = ".png"
        elif mime_type and mime_type.startswith("video/"):
            suffix = ".mp4"
        elif mime_type and mime_type.startswith("audio/"):
            suffix = ".mp3"

        try:
            fd, path = tempfile.mkstemp(prefix="autopost_tg_", suffix=suffix)
            os.close(fd)
            downloaded = await client.download_media(message, file=path)
            final_path = str(downloaded or path)
            self._log_info("telegram media downloaded", message_id=getattr(message, "id", None), path=final_path, mime_type=mime_type)
            return final_path
        except Exception as exc:
            self._log_warning("telegram media download failed", message_id=getattr(message, "id", None), reason=str(exc))
            return None

    def _detect_media_type(self, message, mime_type: str | None) -> ContentType:
        if getattr(message, "photo", None):
            return ContentType.IMAGE
        if getattr(message, "video", None):
            return ContentType.VIDEO
        if getattr(message, "audio", None) or (mime_type and mime_type.startswith("audio/")):
            return ContentType.AUDIO
        if mime_type and mime_type.startswith("video/"):
            return ContentType.VIDEO
        return ContentType.DOCUMENT

    async def _build_message_permalink(self, message) -> str | None:
        username = None
        chat = await message.get_chat()
        username = getattr(chat, "username", None)
        if username:
            return f"https://t.me/{username}/{message.id}"
        return None

    def _extract_chat_id(self, chat) -> str | None:
        if chat is None:
            return None
        chat_id = getattr(chat, "id", None)
        if chat_id is None:
            return None
        return str(chat_id)

    def _extract_peer_id(self, peer) -> int | None:
        for field in ("channel_id", "chat_id", "user_id"):
            value = getattr(peer, field, None)
            if value is not None:
                return value
        return None

    async def _get_client(self, required: bool = False):
        if self._client is None:
            if not self.enabled:
                if required:
                    raise RuntimeError("TelegramAdapter is not configured")
                return None
            self._client = await self._create_client()
        return self._client

    async def _create_client(self):
        TelegramClient, StringSession = self._telethon_client_types()

        if self.string_session:
            session = StringSession(self.string_session)
        else:
            session_path = Path(f"{self.session_name}.session")
            session = str(session_path)

        client = TelegramClient(
            session=session,
            api_id=self.api_id,
            api_hash=self.api_hash,
            receive_updates=self.receive_updates,
            sequential_updates=self.sequential_updates,
        )
        await client.connect()
        if self.bot_token:
            await client.start(bot_token=self.bot_token)
        elif self.string_session:
            if not await client.is_user_authorized():
                raise RuntimeError("Telegram string session is not authorized")
        else:
            raise RuntimeError("Either TELEGRAM_STRING_SESSION or TELEGRAM_BOT_TOKEN must be set")
        return client

    @staticmethod
    def _telethon_client_types():
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError as exc:
            raise RuntimeError(
                "Telethon is not installed. Install project dependencies or pip install telethon"
            ) from exc
        return TelegramClient, StringSession

    @staticmethod
    def _telethon_events_module():
        try:
            from telethon import events
        except ImportError as exc:
            raise RuntimeError(
                "Telethon is not installed. Install project dependencies or pip install telethon"
            ) from exc
        return events
