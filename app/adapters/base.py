from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Awaitable, Callable

from app.services.adapter_runtime import AdapterRuntimeMonitor

from app.domain.enums import Platform
from app.domain.models import UnifiedPost


class BaseAdapter(ABC):
    platform: Platform

    def __init__(self, *, instance_id: str | None = None, log_level: str = "INFO") -> None:
        self.instance_id = instance_id or self.platform.value
        self.runtime_monitor: AdapterRuntimeMonitor | None = None
        self.log_level = (log_level or "INFO").upper()
        self.logger = logging.getLogger(f"autopost_sync.adapter.{self.platform.value}.{self.instance_id}")
        self.logger.setLevel(getattr(logging, self.log_level, logging.INFO))

    def attach_runtime_monitor(self, monitor: AdapterRuntimeMonitor) -> None:
        self.runtime_monitor = monitor
        self.runtime_monitor.ensure(self.instance_id, self.platform.value)

    def _should_emit(self, level_name: str) -> bool:
        current = getattr(logging, self.log_level, logging.INFO)
        desired = getattr(logging, level_name.upper(), logging.INFO)
        return desired >= current

    def _log_info(self, message: str, **extra) -> None:
        self.logger.info(message)
        if self.runtime_monitor and self._should_emit("INFO"):
            self.runtime_monitor.log(self.instance_id, self.platform.value, "info", message, **extra)

    def _log_warning(self, message: str, **extra) -> None:
        self.logger.warning(message)
        if self.runtime_monitor and self._should_emit("WARNING"):
            self.runtime_monitor.log(self.instance_id, self.platform.value, "warning", message, **extra)

    def _log_error(self, message: str, *, code: str | None = None, **extra) -> None:
        self.logger.error(message)
        if self.runtime_monitor:
            self.runtime_monitor.record_error(self.instance_id, self.platform.value, message, code=code, **extra)

    def _set_status(self, status: str, *, connected: bool | None = None) -> None:
        if self.runtime_monitor:
            self.runtime_monitor.set_status(self.instance_id, self.platform.value, status=status, connected=connected)

    def _mark_startup(self) -> None:
        if self.runtime_monitor:
            self.runtime_monitor.mark_startup(self.instance_id, self.platform.value)

    def _mark_shutdown(self) -> None:
        if self.runtime_monitor:
            self.runtime_monitor.mark_shutdown(self.instance_id, self.platform.value)

    def _mark_event_received(self, **extra) -> None:
        if self.runtime_monitor:
            self.runtime_monitor.mark_event_received(self.instance_id, self.platform.value, **extra)

    def _mark_event_ignored(self, reason: str, **extra) -> None:
        if self.runtime_monitor:
            self.runtime_monitor.mark_event_ignored(self.instance_id, self.platform.value, reason, **extra)

    def _mark_publish(self, **extra) -> None:
        if self.runtime_monitor:
            self.runtime_monitor.mark_publish(self.instance_id, self.platform.value, **extra)

    async def startup(self, on_post: Callable[[UnifiedPost], Awaitable[None]] | None = None) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def preprocess_webhook(self, payload: dict, request=None):
        return None

    @abstractmethod
    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
        raise NotImplementedError

    @abstractmethod
    async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
        raise NotImplementedError

    @abstractmethod
    async def delete_post(self, chat_id: str, message_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def edit_post(self, chat_id: str, message_id: str, post: UnifiedPost) -> None:
        raise NotImplementedError

    @abstractmethod
    async def supports_feature(self, feature: str) -> bool:
        raise NotImplementedError
