from __future__ import annotations

import json
import logging
import sys
from typing import Any


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


def _ensure_handler(logger: logging.Logger, *, level: int, marker: str) -> None:
    if any(getattr(h, marker, False) for h in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    setattr(handler, marker, True)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)


def setup_logging(settings) -> None:
    level = _level(getattr(settings, "log_level", None), logging.INFO)

    root = logging.getLogger()
    if root.level > level or root.level == logging.NOTSET:
        root.setLevel(level)
    _ensure_handler(root, level=level, marker="_autopost_sync_root")

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
