from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response

from app.utils.logging import format_extra, get_logger


_REQUEST_LOGGER = get_logger("autopost_sync.request")
_MAX_BODY_LOG_BYTES = 16_384
_REDACTED_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
}
_REDACTED_BODY_KEYS = {
    "access_token",
    "authorization",
    "client_secret",
    "cookie",
    "password",
    "refresh_token",
    "secret",
    "secret_key",
    "tokens",
    "token",
}
_REDACTED_QUERY_PARAM_NAMES = {
    "access_token",
    "client_secret",
    "code",
    "device_id",
    "refresh_token",
    "secret",
    "state",
    "token",
}


def _redact_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if str(key).lower() in _REDACTED_BODY_KEYS else _redact_mapping(inner)
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [_redact_mapping(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_mapping(item) for item in value]
    return value


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: "[redacted]" if key.lower() in _REDACTED_HEADER_NAMES else value
        for key, value in headers.items()
    }


def _redact_query_params(query_params: dict[str, str]) -> dict[str, str]:
    return {
        key: "[redacted]" if key.lower() in _REDACTED_QUERY_PARAM_NAMES else value
        for key, value in query_params.items()
    }


def _extract_request_body(body: bytes, content_type: str | None) -> dict[str, Any]:
    details: dict[str, Any] = {"size": len(body)}
    if not body:
        return details

    truncated = len(body) > _MAX_BODY_LOG_BYTES
    sample = body[:_MAX_BODY_LOG_BYTES]
    text = sample.decode("utf-8", errors="replace")
    details["truncated"] = truncated

    should_try_json = "json" in (content_type or "").lower() or text.lstrip().startswith(("{", "["))
    if should_try_json:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            details["text"] = text
        else:
            details["json"] = _redact_mapping(parsed)
        return details

    details["text"] = text
    return details


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_incoming_request(request: Request, call_next: Callable[[Request], Response]) -> Response:
        started_at = time.perf_counter()
        body = await request.body()
        request_details = {
            "method": request.method,
            "path": request.url.path,
            "query": _redact_query_params(dict(request.query_params)),
            "client": request.client.host if request.client else None,
            "content_type": request.headers.get("content-type"),
            "headers": _redact_headers(dict(request.headers)),
            "body": _extract_request_body(body, request.headers.get("content-type")),
        }
        _REQUEST_LOGGER.info(f"incoming request{format_extra(request_details)}")

        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        _REQUEST_LOGGER.info(
            f"request completed{format_extra({'method': request.method, 'path': request.url.path, 'status_code': response.status_code, 'elapsed_ms': elapsed_ms})}"
        )
        return response
