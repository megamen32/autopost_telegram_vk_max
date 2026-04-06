from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class AdapterRuntimeState:
    instance_id: str
    platform: str
    status: str = "created"
    connected: bool = False
    startup_count: int = 0
    shutdown_count: int = 0
    events_received: int = 0
    events_ignored: int = 0
    posts_published: int = 0
    last_event_at: str | None = None
    last_publish_at: str | None = None
    last_error_at: str | None = None
    last_error: str | None = None
    last_error_code: str | None = None
    logs: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))
    errors: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=30))


class AdapterRuntimeMonitor:
    def __init__(self) -> None:
        self._states: dict[str, AdapterRuntimeState] = {}
        self._global_logs = deque(maxlen=400)
        self._lock = Lock()

    def ensure(self, instance_id: str, platform: str) -> AdapterRuntimeState:
        with self._lock:
            state = self._states.get(instance_id)
            if state is None:
                state = AdapterRuntimeState(instance_id=instance_id, platform=platform)
                self._states[instance_id] = state
            return state

    def log(self, instance_id: str, platform: str, level: str, message: str, **extra: Any) -> None:
        state = self.ensure(instance_id, platform)
        entry = {"ts": utcnow_iso(), "level": level, "message": message, "extra": extra or None}
        state.logs.appendleft(entry)
        self._global_logs.appendleft({**entry, "instance_id": instance_id, "platform": platform})

    def set_status(self, instance_id: str, platform: str, *, status: str, connected: bool | None = None) -> None:
        state = self.ensure(instance_id, platform)
        state.status = status
        if connected is not None:
            state.connected = connected
        self.log(instance_id, platform, "info", f"status={status}", connected=state.connected)

    def mark_startup(self, instance_id: str, platform: str) -> None:
        state = self.ensure(instance_id, platform)
        state.startup_count += 1
        self.log(instance_id, platform, "info", "startup")

    def mark_shutdown(self, instance_id: str, platform: str) -> None:
        state = self.ensure(instance_id, platform)
        state.shutdown_count += 1
        state.connected = False
        state.status = "stopped"
        self.log(instance_id, platform, "info", "shutdown")

    def mark_event_received(self, instance_id: str, platform: str, **extra: Any) -> None:
        state = self.ensure(instance_id, platform)
        state.events_received += 1
        state.last_event_at = utcnow_iso()
        self.log(instance_id, platform, "info", "event_received", **extra)

    def mark_event_ignored(self, instance_id: str, platform: str, reason: str, **extra: Any) -> None:
        state = self.ensure(instance_id, platform)
        state.events_ignored += 1
        self.log(instance_id, platform, "warning", f"event_ignored: {reason}", **extra)

    def mark_publish(self, instance_id: str, platform: str, **extra: Any) -> None:
        state = self.ensure(instance_id, platform)
        state.posts_published += 1
        state.last_publish_at = utcnow_iso()
        self.log(instance_id, platform, "info", "publish", **extra)

    def record_error(self, instance_id: str, platform: str, message: str, *, code: str | None = None, **extra: Any) -> None:
        state = self.ensure(instance_id, platform)
        state.last_error = message
        state.last_error_at = utcnow_iso()
        state.last_error_code = code
        entry = {"ts": state.last_error_at, "message": message, "code": code, "extra": extra or None}
        state.errors.appendleft(entry)
        log_entry = {"ts": state.last_error_at, "level": "error", "message": message, "extra": extra or None}
        state.logs.appendleft(log_entry)
        self._global_logs.appendleft({**log_entry, "instance_id": instance_id, "platform": platform})

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "instance_id": s.instance_id,
                    "platform": s.platform,
                    "status": s.status,
                    "connected": s.connected,
                    "startup_count": s.startup_count,
                    "shutdown_count": s.shutdown_count,
                    "events_received": s.events_received,
                    "events_ignored": s.events_ignored,
                    "posts_published": s.posts_published,
                    "last_event_at": s.last_event_at,
                    "last_publish_at": s.last_publish_at,
                    "last_error_at": s.last_error_at,
                    "last_error": s.last_error,
                    "last_error_code": s.last_error_code,
                    "logs": list(s.logs),
                    "errors": list(s.errors),
                }
                for s in sorted(self._states.values(), key=lambda x: x.instance_id)
            ]


    def global_logs(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._global_logs)
