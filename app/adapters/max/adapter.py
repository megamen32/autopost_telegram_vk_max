from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from fastapi import Request

from app.adapters.base import BaseAdapter
from app.adapters.max.client import MaxClient
from app.adapters.max.publisher import MaxPublisher
from app.adapters.max.webhook import MaxWebhookHandler
from app.domain.enums import Platform
from app.domain.models import UnifiedPost

logger = logging.getLogger(__name__)


class MaxAdapter(BaseAdapter):
    platform = Platform.MAX

    def __init__(
        self,
        *,
        instance_id: str | None = None,
        token: str | None = None,
        webhook_url: str | None = None,
        secret: str | None = None,
        update_types: list[str] | None = None,
        receive_updates: bool = True,
        receive_mode: str = "long_poll",
        allowed_source_chat_ids: list[str] | None = None,
        prefer_official_sdk: bool = True,
        long_poll_timeout_seconds: int = 30,
        long_poll_limit: int = 100,
        log_level: str = "INFO",
    ) -> None:
        super().__init__(instance_id=instance_id, log_level=log_level)
        self.token = token
        self.webhook_url = webhook_url
        self.secret = secret
        self.update_types = update_types or ["message_created"]
        self.receive_updates = receive_updates
        self.receive_mode = receive_mode or "long_poll"
        self.allowed_source_chat_ids = allowed_source_chat_ids or []
        self.prefer_official_sdk = prefer_official_sdk
        self.long_poll_timeout_seconds = long_poll_timeout_seconds
        self.long_poll_limit = long_poll_limit
        self._on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None
        self._client: MaxClient | None = None
        self._publisher: MaxPublisher | None = None
        self._polling_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._marker: int | None = None
        self._webhook_handler = MaxWebhookHandler(
            instance_id=self.instance_id,
            secret=self.secret,
            allowed_source_chat_ids=self.allowed_source_chat_ids,
        )

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def _get_client(self) -> MaxClient:
        if self._client is None:
            if not self.token:
                raise RuntimeError("MAX token is not configured")
            self._client = MaxClient(self.token, prefer_sdk=self.prefer_official_sdk)
        return self._client

    def _get_publisher(self) -> MaxPublisher:
        if self._publisher is None:
            self._publisher = MaxPublisher(self._get_client())
        return self._publisher

    async def startup(self, on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None) -> None:
        self._on_post = on_post
        self._stop_event.clear()
        self._mark_startup()
        if not self.enabled:
            self._log_warning("max disabled: token not configured")
            self._set_status("disabled", connected=False)
            return
        if self.receive_updates and on_post is not None and self.receive_mode == "long_poll":
            try:
                await self._get_client().delete_webhook_subscriptions()
            except Exception:
                logger.info(f"MAX webhook cleanup skipped for {self.instance_id}")
            self._polling_task = asyncio.create_task(self._run_long_poll_loop(), name=f"max-long-poll-{self.instance_id}")
            self._set_status("running", connected=True)
            self._log_info("max long poll started")
            return
        if self.receive_updates and self.webhook_url:
            try:
                await self._get_client().subscribe_webhook(
                    url=self.webhook_url,
                    update_types=self.update_types,
                    secret=self.secret,
                )
                self._set_status("running", connected=True)
                self._log_info("max webhook subscription registered")
            except Exception:
                self._log_error("failed to register MAX webhook subscription", code="max_webhook_subscribe_failed")

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

    async def _run_long_poll_loop(self) -> None:
        if self._on_post is None:
            return
        client = self._get_client()
        while not self._stop_event.is_set():
            try:
                response = await client.get_updates(
                    limit=self.long_poll_limit,
                    timeout=self.long_poll_timeout_seconds,
                    marker=self._marker,
                    types=self.update_types,
                )
                self._marker = response.get("marker", self._marker)
                for update in response.get("updates") or []:
                    post = await self.parse_incoming_event(update)
                    if post is not None:
                        self._mark_event_received(chat_id=post.source_chat_id, message_id=post.source_message_id)
                        await self._on_post(post)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._log_error(f"max long poll loop failed: {exc}", code="max_long_poll_failed")
                await asyncio.sleep(3)

    async def preprocess_webhook(self, payload: dict, request: Request | None = None):
        return await self._webhook_handler.preprocess_webhook(payload, request=request)

    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
        post = self._webhook_handler.parse_incoming_event(payload)
        if post is None:
            self._mark_event_ignored("unsupported_max_payload")
            return None
        if self.allowed_source_chat_ids and post.source_chat_id not in self.allowed_source_chat_ids:
            self._mark_event_ignored("chat_not_allowed", chat_id=post.source_chat_id)
            return None
        return post

    async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
        if not self.enabled:
            self._mark_publish(chat_id=chat_id, dry_run=True)
            return f"max-dry-run-{chat_id}-{post.source_message_id}"
        result = await self._get_publisher().publish_post(chat_id, post)
        self._mark_publish(chat_id=chat_id, message_id=result)
        return result

    async def delete_post(self, chat_id: str, message_id: str) -> None:
        if not self.enabled:
            return None
        await self._get_publisher().delete_post(chat_id, message_id)
        return None

    async def edit_post(self, chat_id: str, message_id: str, post: UnifiedPost) -> None:
        if not self.enabled:
            return None
        await self._get_publisher().edit_post(chat_id, message_id, post)
        return None

    async def supports_feature(self, feature: str) -> bool:
        return feature in {"text", "image", "video", "audio", "document", "edit", "delete", "webhook", "long_poll"}
