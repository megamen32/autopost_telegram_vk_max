from __future__ import annotations

import json
import logging
import sys
from collections import deque
from threading import Lock
from typing import Any


_GLOBAL_LOGS = deque(maxlen=500)
_GLOBAL_LOCK = Lock()


def _level(value: str | None, default: int = logging.INFO) -> int:
    if not value:
        return default
    return getattr(logging, str(value).upper(), default)


def format_extra(extra: dict[str, Any] | None) -> str:
    if not extra:
        return ""
    try:
        return " | " + json.dumps(extra, ensure_ascii=False, default=str, sort_keys=True)
    except Exception:
        return " | " + repr(extra)


class GlobalDiagnosticsHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if not str(record.name).startswith('autopost_sync'):
            return
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        payload = {
            'ts': getattr(record, 'created', None),
            'level': record.levelname,
            'logger': record.name,
            'message': msg,
        }
        with _GLOBAL_LOCK:
            _GLOBAL_LOGS.appendleft(payload)


def get_global_logs() -> list[dict[str, Any]]:
    with _GLOBAL_LOCK:
        return list(_GLOBAL_LOGS)


def _ensure_handler(logger: logging.Logger, *, level: int, marker: str) -> None:
    if any(getattr(h, marker, False) for h in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    setattr(handler, marker, True)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)


def _ensure_global_handler(logger: logging.Logger, *, marker: str) -> None:
    if any(getattr(h, marker, False) for h in logger.handlers):
        return
    handler = GlobalDiagnosticsHandler()
    setattr(handler, marker, True)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def setup_logging(settings) -> None:
    level = _level(getattr(settings, "log_level", None), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    _ensure_handler(root, level=level, marker="_autopost_sync_root")
    _ensure_global_handler(root, marker='_autopost_sync_global')

    project_logger = logging.getLogger("autopost_sync")
    project_logger.setLevel(level)
    project_logger.propagate = True

    for name in [
        "autopost_sync.app",
        "autopost_sync.routes",
        "autopost_sync.pipeline",
        "autopost_sync.worker",
        "autopost_sync.adapter",
    ]:
        child = logging.getLogger(name)
        child.setLevel(level)
        child.propagate = True

    logging.captureWarnings(True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
