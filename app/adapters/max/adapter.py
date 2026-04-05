from __future__ import annotations

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
        allowed_source_chat_ids: list[str] | None = None,
        prefer_official_sdk: bool = True,
    ) -> None:
        super().__init__(instance_id=instance_id)
        self.token = token
        self.webhook_url = webhook_url
        self.secret = secret
        self.update_types = update_types or ["message_created"]
        self.receive_updates = receive_updates
        self.allowed_source_chat_ids = allowed_source_chat_ids or []
        self.prefer_official_sdk = prefer_official_sdk
        self._on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None
        self._client: MaxClient | None = None
        self._publisher: MaxPublisher | None = None
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
        if not self.enabled:
            logger.info("MaxAdapter disabled: no MAX token configured")
            return
        if self.receive_updates and self.webhook_url:
            try:
                await self._get_client().subscribe_webhook(
                    url=self.webhook_url,
                    update_types=self.update_types,
                    secret=self.secret,
                )
                logger.info("MAX webhook subscription registered for %s", self.instance_id)
            except Exception:
                logger.exception("Failed to register MAX webhook subscription for %s", self.instance_id)

    async def preprocess_webhook(self, payload: dict, request: Request | None = None):
        return await self._webhook_handler.preprocess_webhook(payload, request=request)

    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
        return self._webhook_handler.parse_incoming_event(payload)

    async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
        if not self.enabled:
            return f"max-dry-run-{chat_id}-{post.source_message_id}"
        return await self._get_publisher().publish_post(chat_id, post)

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
        return feature in {"text", "image", "video", "audio", "document", "edit", "delete", "webhook"}
