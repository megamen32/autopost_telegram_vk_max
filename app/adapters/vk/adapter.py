from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Any, Awaitable, Callable

from fastapi import HTTPException

from app.adapters.base import BaseAdapter
from app.adapters.common import parse_media_items
from app.adapters.vk.browser_publisher import VkBrowserPublisher
from app.adapters.vk.client import VkApiError, VkClient
from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost
from app.services.vk_oauth import compute_expires_at, is_token_expired, refresh_access_token

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
        user_access_token_for_media: str | None = None,
        vk_id_client_id: str | None = None,
        vk_oauth_refresh_token: str | None = None,
        vk_oauth_device_id: str | None = None,
        vk_oauth_token_expires_at: int | str | None = None,
        browser_cdp_url: str | None = None,
        log_level: str = "INFO",
    ) -> None:
        super().__init__(instance_id=instance_id, log_level=log_level)
        self.token = token
        self.group_id = group_id
        self.api_version = api_version
        self.confirmation_token = confirmation_token
        self.secret = secret
        self.receive_updates = receive_updates
        self.receive_mode = receive_mode or "long_poll"
        self.long_poll_wait_seconds = long_poll_wait_seconds
        self.user_access_token_for_media = user_access_token_for_media
        self.vk_id_client_id = str(vk_id_client_id or "").strip() or None
        self.vk_oauth_refresh_token = str(vk_oauth_refresh_token or "").strip() or None
        self.vk_oauth_device_id = str(vk_oauth_device_id or "").strip() or None
        self.vk_oauth_token_expires_at = self._coerce_int(vk_oauth_token_expires_at)
        self.browser_cdp_url = browser_cdp_url
        self.allowed_source_chat_ids = set(allowed_source_chat_ids or [])
        self._client: VkClient | None = None
        self._receive_client: VkClient | None = None
        self._on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None
        self._polling_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._token_refresh_lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.group_id and (self._has_api_credentials() or self._has_browser_fallback()))

    def _get_client(self) -> VkClient:
        token = self._get_publish_token()
        if self._client is None or self._client.token != token:
            if not self.enabled or not token:
                raise RuntimeError("VkAdapter is not configured")
            self._client = VkClient(token, api_version=self.api_version)
        return self._client

    def _get_receive_client(self) -> VkClient:
        token = str(self.token or "").strip()
        if self._receive_client is None or self._receive_client.token != token:
            if not token:
                raise RuntimeError("VkAdapter receive client is not configured")
            self._receive_client = VkClient(token, api_version=self.api_version)
        return self._receive_client

    def _media_token_candidates(self) -> list[str]:
        tokens: list[str] = []
        for token in (self.user_access_token_for_media, self.token):
            if token and token not in tokens:
                tokens.append(token)
        return tokens

    def _get_publish_token(self) -> str | None:
        return self.user_access_token_for_media or self.token

    def _can_refresh_user_token(self) -> bool:
        return bool(self.vk_id_client_id and self.vk_oauth_refresh_token and self.vk_oauth_device_id)

    async def _refresh_user_token_if_needed(self, *, force: bool = False) -> bool:
        if not self._can_refresh_user_token():
            return False

        should_refresh = force or not self.user_access_token_for_media
        if not should_refresh and self.user_access_token_for_media:
            should_refresh = is_token_expired(self.vk_oauth_token_expires_at)
        if not should_refresh:
            return False

        async with self._token_refresh_lock:
            if not force and self.user_access_token_for_media and not is_token_expired(self.vk_oauth_token_expires_at):
                return False

            tokens = await refresh_access_token(
                client_id=str(self.vk_id_client_id),
                refresh_token=str(self.vk_oauth_refresh_token),
                device_id=str(self.vk_oauth_device_id),
            )
            access_token = str(tokens.get("access_token") or "").strip()
            if not access_token:
                raise RuntimeError("VK refresh response does not contain access_token")

            self.user_access_token_for_media = access_token
            next_refresh_token = str(tokens.get("refresh_token") or "").strip()
            if next_refresh_token:
                self.vk_oauth_refresh_token = next_refresh_token
            self.vk_oauth_token_expires_at = compute_expires_at(tokens.get("expires_in"))
            self._client = None
            self._log_info("vk user token refreshed", expires_at=self.vk_oauth_token_expires_at)
            return True

    def _should_retry_after_refresh(self, exc: Exception) -> bool:
        return bool(self.user_access_token_for_media and self._can_refresh_user_token() and isinstance(exc, VkApiError) and exc.is_auth_error)

    def _log_vk_api_guidance(self, exc: Exception) -> None:
        if not isinstance(exc, VkApiError):
            return
        if exc.error_code in {15, 27, 1051}:
            self._log_warning(
                "vk official api rejected current token for publishing; prefer VK user token via VK ID and keep group token only for incoming events",
                error_code=exc.error_code,
                error_msg=exc.error_msg,
                method=exc.method,
            )

    async def startup(self, on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None) -> None:
        self._on_post = on_post
        self._stop_event.clear()
        if not self.enabled:
            logger.info("VkAdapter disabled: no VK credentials configured")
            self._log_warning("vk disabled: missing group_id and token/user oauth token")
            return
        self._set_status("running", connected=bool(self._has_api_credentials() or self._has_browser_fallback()))
        if self.receive_updates and not self.token:
            self._log_warning("vk receive_updates requested, but group token is missing; outgoing publishing may work, incoming VK events will not start")
        if self.receive_updates and self.receive_mode == "long_poll" and on_post is not None and self.token:
            self._polling_task = asyncio.create_task(self._run_long_poll_loop(), name=f"vk-long-poll-{self.instance_id}")
            self._log_info("vk long poll started")
        elif self.receive_updates and self.receive_mode == "webhook" and not self.token:
            self._log_warning("vk webhook/long poll listener not started: group token is required for incoming VK events")

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
        if self._has_api_credentials():
            try:
                await self._refresh_user_token_if_needed()
            except Exception as exc:
                self._log_warning(f"vk token refresh failed before publish; continuing with current credentials: {exc}")
            try:
                return await self._publish_post_via_api(owner_id=owner_id, post=post)
            except Exception as exc:
                if self._should_retry_after_refresh(exc):
                    await self._refresh_user_token_if_needed(force=True)
                    return await self._publish_post_via_api(owner_id=owner_id, post=post)
                self._log_vk_api_guidance(exc)
                if not self._has_browser_fallback():
                    raise
                self._log_warning(f"vk api publish failed, switching to browser fallback: {exc}")

        if self._has_browser_fallback():
            return await self._publish_post_via_browser(owner_id=owner_id, post=post)

        raise RuntimeError("VkAdapter has no publishing method configured")

    async def _publish_post_via_api(self, *, owner_id: int, post: UnifiedPost) -> str:
        client = self._get_client()

        attachments: list[str] = []
        append_links_to_text: list[str] = []

        for item in post.media:
            attachment = await self._prepare_attachment(client=client, owner_id=owner_id, item=item)
            if attachment is None:
                fallback_link = item.url or item.file_id
                self._log_warning("vk attachment fallback to link/text", media_type=item.type.value, fallback_link=fallback_link)
                if fallback_link and str(fallback_link).startswith(("http://", "https://")):
                    append_links_to_text.append(fallback_link)
                continue
            self._log_info("vk attachment prepared", media_type=item.type.value, attachment=attachment)
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

    async def _publish_post_via_browser(self, *, owner_id: int, post: UnifiedPost) -> str:
        browser_cdp_url = str(self.browser_cdp_url or "").strip()
        if not browser_cdp_url:
            raise VkApiError("vk browser cdp url is not configured")

        browser_post_text = self._build_browser_post_text(post)
        browser_publisher = VkBrowserPublisher(
            cdp_url=browser_cdp_url,
            group_id=abs(owner_id),
        )
        post_id = await browser_publisher.publish_post(
            text=browser_post_text,
            media=post.media,
        )
        self._log_info("vk browser fallback publish success", post_id=post_id, owner_id=owner_id)
        return post_id

    async def delete_post(self, chat_id: str, message_id: str) -> None:
        if not self.enabled:
            return None
        await self._refresh_user_token_if_needed()
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
        await self._refresh_user_token_if_needed()
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

    def _has_api_credentials(self) -> bool:
        return bool(self.token or self.user_access_token_for_media or self._can_refresh_user_token())

    def _has_browser_fallback(self) -> bool:
        return bool(str(self.browser_cdp_url or "").strip())

    def _build_browser_post_text(self, post: UnifiedPost) -> str:
        return post.text or ""

    async def _run_long_poll_loop(self) -> None:
        if self._on_post is None:
            return
        client = self._get_receive_client()
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
                client = self._get_receive_client()
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

        candidates = self._media_token_candidates()
        if not candidates:
            return None

        if item.type == ContentType.IMAGE and (item.url or item.file_id):
            self._log_info("vk image upload start", source=item.url or item.file_id, filename=item.filename)
            return await self._upload_with_candidates(
                candidates=candidates,
                media_label="image",
                attempt=lambda media_client: self._upload_wall_photo(media_client=media_client, owner_id=owner_id, item=item),
            )

        if item.type == ContentType.DOCUMENT and (item.url or item.file_id):
            if not item.url and item.file_id and _ATTACHMENT_RE.match(str(item.file_id)):
                return str(item.file_id)
            self._log_info("vk document upload start", source=item.url or item.file_id, filename=item.filename)
            return await self._upload_with_candidates(
                candidates=candidates,
                media_label="document",
                attempt=lambda media_client: self._upload_wall_document(media_client=media_client, owner_id=owner_id, item=item),
            )

        if item.type == ContentType.VIDEO and (item.url or item.file_id):
            if item.file_id and _ATTACHMENT_RE.match(str(item.file_id)):
                return str(item.file_id)
            self._log_info("vk video upload start", source=item.url or item.file_id, filename=item.filename)
            return await self._upload_with_candidates(
                candidates=candidates,
                media_label="video",
                attempt=lambda media_client: self._upload_wall_video(media_client=media_client, owner_id=owner_id, item=item),
            )

        if item.type == ContentType.AUDIO and (item.url or item.file_id):
            if item.file_id and _ATTACHMENT_RE.match(str(item.file_id)):
                return str(item.file_id)
            self._log_info("vk audio upload start", source=item.url or item.file_id, filename=item.filename)
            return await self._upload_with_candidates(
                candidates=candidates,
                media_label="audio",
                attempt=lambda media_client: self._upload_wall_audio(media_client=media_client, owner_id=owner_id, item=item),
            )

        return None

    async def _upload_with_candidates(
        self,
        *,
        candidates: list[str],
        media_label: str,
        attempt: Callable[[VkClient], Awaitable[str]],
    ) -> str:
        for idx, token in enumerate(candidates):
            media_client = VkClient(token, api_version=self.api_version)
            if idx == 0 and len(candidates) > 1:
                self._log_warning(f"vk {media_label} upload trying preferred token first; fallback candidates={len(candidates) - 1}")
            try:
                return await attempt(media_client)
            except Exception as exc:
                if idx < len(candidates) - 1:
                    self._log_warning(f"vk {media_label} upload failed with one token, trying fallback: {exc}")
                    continue
                raise
        raise RuntimeError(f"vk {media_label} upload failed")

    async def _upload_wall_photo(self, *, media_client: VkClient, owner_id: int, item: MediaItem) -> str:
        upload_server = await media_client.call_method(
            "photos.getWallUploadServer",
            {"group_id": abs(owner_id)},
        )
        content = await media_client.download_bytes(str(item.url or item.file_id))
        upload_result = await media_client.upload_file(
            upload_server["upload_url"],
            form_field="photo",
            filename=item.filename or "image.jpg",
            content=content,
            content_type=item.mime_type,
        )
        saved = await media_client.call_method(
            "photos.saveWallPhoto",
            {
                "group_id": abs(owner_id),
                "photo": upload_result["photo"],
                "server": upload_result["server"],
                "hash": upload_result["hash"],
            },
        )
        photo = saved[0] if isinstance(saved, list) else self._first_payload(saved, "photo")
        attachment = self._build_attachment_ref("photo", photo)
        if attachment is None:
            raise RuntimeError("VK photo upload response does not contain attachment data")
        self._log_info("vk image upload success", attachment=attachment)
        return attachment

    async def _upload_wall_document(self, *, media_client: VkClient, owner_id: int, item: MediaItem) -> str:
        upload_server = await media_client.call_method(
            "docs.getWallUploadServer",
            {"group_id": abs(owner_id)},
        )
        content = await media_client.download_bytes(str(item.url or item.file_id))
        upload_result = await media_client.upload_file(
            upload_server["upload_url"],
            form_field="file",
            filename=item.filename or "document.bin",
            content=content,
            content_type=item.mime_type,
        )
        saved = await media_client.call_method("docs.save", {"file": upload_result["file"]})
        doc = self._first_payload(saved, "doc", "response")
        attachment = self._build_attachment_ref("doc", doc)
        if attachment is None:
            raise RuntimeError("VK document upload response does not contain attachment data")
        return attachment

    async def _upload_wall_video(self, *, media_client: VkClient, owner_id: int, item: MediaItem) -> str:
        upload_server = await media_client.call_method(
            "video.save",
            {
                "group_id": abs(owner_id),
                "name": item.filename or "video",
                "wallpost": 1,
            },
        )
        content = await media_client.download_bytes(str(item.url or item.file_id))
        upload_result = await media_client.upload_file(
            upload_server["upload_url"],
            form_field="video_file",
            filename=item.filename or "video.mp4",
            content=content,
            content_type=item.mime_type,
        )
        video_payload = self._first_payload(upload_result, "video", "response") or self._first_payload(upload_server, "video", "response")
        attachment = self._build_attachment_ref("video", video_payload)
        if attachment is None:
            raise RuntimeError("VK video upload response does not contain attachment data")
        return attachment

    async def _upload_wall_audio(self, *, media_client: VkClient, owner_id: int, item: MediaItem) -> str:
        upload_server = await media_client.call_method("audio.getUploadServer", {})
        content = await media_client.download_bytes(str(item.url or item.file_id))
        upload_result = await media_client.upload_file(
            upload_server["upload_url"],
            form_field="file",
            filename=item.filename or "audio.mp3",
            content=content,
            content_type=item.mime_type,
        )
        saved = await media_client.call_method(
            "audio.save",
            {
                "server": upload_result["server"],
                "audio": upload_result["audio"],
                "hash": upload_result["hash"],
            },
        )
        audio_payload = self._first_payload(saved, "audio", "response")
        attachment = self._build_attachment_ref("audio", audio_payload)
        if attachment is None:
            raise RuntimeError("VK audio upload response does not contain attachment data")
        return attachment

    @staticmethod
    def _first_payload(value: Any, *preferred_keys: str) -> dict[str, Any] | None:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    return item
            return None
        if not isinstance(value, dict):
            return None
        for key in preferred_keys:
            nested = value.get(key)
            if isinstance(nested, dict):
                return nested
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        return item
        return value

    @staticmethod
    def _build_attachment_ref(media_type: str, payload: dict[str, Any] | None) -> str | None:
        if not payload:
            return None
        owner_id = payload.get("owner_id")
        if owner_id is None:
            return None

        media_id: Any | None = None
        if media_type == "photo":
            media_id = payload.get("id")
        elif media_type == "video":
            media_id = payload.get("video_id") or payload.get("id") or payload.get("vid")
        elif media_type == "audio":
            media_id = payload.get("audio_id") or payload.get("id") or payload.get("aid")
        elif media_type == "doc":
            media_id = payload.get("doc_id") or payload.get("id") or payload.get("did")
        else:
            media_id = payload.get("id")

        if media_id is None:
            return None

        attachment = f"{media_type}{owner_id}_{media_id}"
        access_key = payload.get("access_key")
        if access_key:
            attachment = f"{attachment}_{access_key}"
        return attachment

    @staticmethod
    def _coerce_int(value: int | str | None) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
