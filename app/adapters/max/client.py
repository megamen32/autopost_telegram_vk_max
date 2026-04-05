from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
from pathlib import Path
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)


class MaxApiError(RuntimeError):
    pass


class MaxTransport(Protocol):
    async def get_me(self) -> dict[str, Any]: ...
    async def send_message(
        self,
        *,
        chat_id: int | None = None,
        user_id: int | None = None,
        body: dict[str, Any],
        disable_link_preview: bool | None = None,
    ) -> dict[str, Any]: ...
    async def edit_message(self, message_id: int, body: dict[str, Any]) -> dict[str, Any]: ...
    async def delete_message(self, message_id: int) -> dict[str, Any]: ...
    async def subscribe_webhook(self, *, url: str, update_types: list[str], secret: str | None = None) -> dict[str, Any]: ...
    async def delete_webhook_subscriptions(self) -> dict[str, Any]: ...
    async def get_updates(self, *, limit: int = 100, timeout: int = 30, marker: int | None = None, types: list[str] | None = None) -> dict[str, Any]: ...
    async def upload_attachment(
        self,
        *,
        upload_type: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        wait_ready: bool = True,
    ) -> dict[str, Any]: ...
    async def download_bytes(self, location: str) -> bytes: ...


class HttpxMaxTransport:
    def __init__(self, token: str, base_url: str = "https://platform-api.max.ru") -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self.token}

    async def get_me(self) -> dict[str, Any]:
        return await self.call_api("GET", "/me")

    async def call_api(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=self._headers(),
                params=params,
                json=json_body,
            )
            response.raise_for_status()
            data = response.json()
        if isinstance(data, dict) and data.get("code"):
            raise MaxApiError(f"MAX API error for {method} {path}: {data}")
        return data

    async def send_message(
        self,
        *,
        chat_id: int | None = None,
        user_id: int | None = None,
        body: dict[str, Any],
        disable_link_preview: bool | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if chat_id is not None:
            params["chat_id"] = chat_id
        if user_id is not None:
            params["user_id"] = user_id
        if disable_link_preview is not None:
            params["disable_link_preview"] = disable_link_preview
        return await self.call_api("POST", "/messages", params=params, json_body=body)

    async def edit_message(self, message_id: int, body: dict[str, Any]) -> dict[str, Any]:
        return await self.call_api("PUT", f"/messages/{message_id}", json_body=body)

    async def delete_message(self, message_id: int) -> dict[str, Any]:
        return await self.call_api("DELETE", f"/messages/{message_id}")

    async def subscribe_webhook(self, *, url: str, update_types: list[str], secret: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"url": url, "update_types": update_types}
        if secret:
            body["secret"] = secret
        return await self.call_api("POST", "/subscriptions", json_body=body)

    async def delete_webhook_subscriptions(self) -> dict[str, Any]:
        return await self.call_api("DELETE", "/subscriptions")

    async def get_updates(
        self,
        *,
        limit: int = 100,
        timeout: int = 30,
        marker: int | None = None,
        types: list[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "timeout": timeout}
        if marker is not None:
            params["marker"] = marker
        if types:
            params["types"] = types
        return await self.call_api("GET", "/updates", params=params)

    async def get_upload_url(self, upload_type: str) -> dict[str, Any]:
        return await self.call_api("POST", "/uploads", params={"type": upload_type})

    async def upload_file(
        self,
        upload_url: str,
        *,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        files = {"data": (filename, content, content_type or "application/octet-stream")}
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(upload_url, headers=self._headers(), files=files)
            response.raise_for_status()
            return response.json()

    async def download_bytes(self, location: str) -> bytes:
        if location.startswith("http://") or location.startswith("https://"):
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                response = await client.get(location)
                response.raise_for_status()
                return response.content
        return Path(location).read_bytes()

    async def upload_attachment(
        self,
        *,
        upload_type: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        wait_ready: bool = True,
    ) -> dict[str, Any]:
        upload_info = await self.get_upload_url(upload_type)
        upload_response = await self.upload_file(
            upload_info["url"],
            filename=filename,
            content=content,
            content_type=content_type,
        )
        if upload_type in {"video", "audio"}:
            token = upload_info.get("token") or upload_response.get("token")
            payload = {"token": token}
        else:
            payload = upload_response
        if wait_ready and upload_type in {"video", "audio", "image", "file"}:
            await asyncio.sleep(1.0)
        return {"type": upload_type, "payload": payload}


class MaxApiSdkTransport:
    """Thin adapter over official/fork-verified maxapi package.

    The package surface may evolve, so this class keeps the dependency isolated.
    When a required method is missing, caller should fall back to HttpxMaxTransport.
    """

    def __init__(self, token: str) -> None:
        self.token = token
        try:
            self.maxapi = importlib.import_module("maxapi")
        except Exception as exc:  # pragma: no cover - depends on environment
            raise RuntimeError("maxapi package is not installed") from exc
        bot_cls = getattr(self.maxapi, "Bot", None)
        if bot_cls is None:
            raise RuntimeError("maxapi.Bot not found")
        self.bot = bot_cls(token)

    async def _maybe_call(self, *names: str, **kwargs):
        target = self.bot
        method = None
        for name in names:
            method = getattr(target, name, None)
            if method is not None:
                break
        if method is None:
            raise RuntimeError(f"Required maxapi method missing: {names}")
        result = method(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def get_me(self) -> dict[str, Any]:
        result = await self._maybe_call("get_me", "me")
        return _to_dict(result)

    async def send_message(self, *, chat_id: int | None = None, user_id: int | None = None, body: dict[str, Any], disable_link_preview: bool | None = None) -> dict[str, Any]:
        params = {}
        if chat_id is not None:
            params["chat_id"] = chat_id
        if user_id is not None:
            params["user_id"] = user_id
        if disable_link_preview is not None:
            params["disable_link_preview"] = disable_link_preview
        params.update(body)
        result = await self._maybe_call("send_message", "create_message", **params)
        return _to_dict(result)

    async def edit_message(self, message_id: int, body: dict[str, Any]) -> dict[str, Any]:
        result = await self._maybe_call("edit_message", message_id=message_id, **body)
        return _to_dict(result)

    async def delete_message(self, message_id: int) -> dict[str, Any]:
        result = await self._maybe_call("delete_message", message_id=message_id)
        return _to_dict(result)

    async def subscribe_webhook(self, *, url: str, update_types: list[str], secret: str | None = None) -> dict[str, Any]:
        result = await self._maybe_call("set_webhook", "subscribe_webhook", url=url, update_types=update_types, secret=secret)
        return _to_dict(result)

    async def delete_webhook_subscriptions(self) -> dict[str, Any]:
        result = await self._maybe_call("delete_webhook", "delete_subscriptions")
        return _to_dict(result)

    async def get_updates(self, *, limit: int = 100, timeout: int = 30, marker: int | None = None, types: list[str] | None = None) -> dict[str, Any]:
        result = await self._maybe_call("get_updates", limit=limit, timeout=timeout, marker=marker, types=types)
        return _to_dict(result)

    async def upload_attachment(self, *, upload_type: str, filename: str, content: bytes, content_type: str | None = None, wait_ready: bool = True) -> dict[str, Any]:
        # maxapi surface is not stable enough here; use httpx fallback in builder instead.
        raise RuntimeError("upload_attachment is not implemented for maxapi transport")

    async def download_bytes(self, location: str) -> bytes:
        return await HttpxMaxTransport(self.token).download_bytes(location)


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {"result": value}


class MaxClient:
    def __init__(self, token: str, *, base_url: str = "https://platform-api.max.ru", prefer_sdk: bool = True) -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.prefer_sdk = prefer_sdk
        self._sdk_transport: MaxTransport | None = None
        self._http_transport: MaxTransport | None = None

    def _http(self) -> MaxTransport:
        if self._http_transport is None:
            self._http_transport = HttpxMaxTransport(self.token, base_url=self.base_url)
        return self._http_transport

    def _sdk(self) -> MaxTransport:
        if self._sdk_transport is None:
            self._sdk_transport = MaxApiSdkTransport(self.token)
        return self._sdk_transport

    async def _prefer_sdk_call(self, method_name: str, *args, **kwargs):
        if self.prefer_sdk:
            try:
                method = getattr(self._sdk(), method_name)
                return await method(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - depends on optional package
                logger.info("MAX SDK transport unavailable for %s, fallback to HTTP: %s", method_name, exc)
        method = getattr(self._http(), method_name)
        return await method(*args, **kwargs)

    async def get_me(self) -> dict[str, Any]:
        return await self._prefer_sdk_call("get_me")

    async def send_message(self, *, chat_id: int | None = None, user_id: int | None = None, body: dict[str, Any], disable_link_preview: bool | None = None) -> dict[str, Any]:
        return await self._prefer_sdk_call(
            "send_message",
            chat_id=chat_id,
            user_id=user_id,
            body=body,
            disable_link_preview=disable_link_preview,
        )

    async def edit_message(self, message_id: int, body: dict[str, Any]) -> dict[str, Any]:
        return await self._prefer_sdk_call("edit_message", message_id, body)

    async def delete_message(self, message_id: int) -> dict[str, Any]:
        return await self._prefer_sdk_call("delete_message", message_id)

    async def subscribe_webhook(self, *, url: str, update_types: list[str], secret: str | None = None) -> dict[str, Any]:
        return await self._prefer_sdk_call("subscribe_webhook", url=url, update_types=update_types, secret=secret)

    async def delete_webhook_subscriptions(self) -> dict[str, Any]:
        return await self._prefer_sdk_call("delete_webhook_subscriptions")

    async def get_updates(self, *, limit: int = 100, timeout: int = 30, marker: int | None = None, types: list[str] | None = None) -> dict[str, Any]:
        return await self._prefer_sdk_call("get_updates", limit=limit, timeout=timeout, marker=marker, types=types)

    async def upload_attachment(self, *, upload_type: str, filename: str, content: bytes, content_type: str | None = None, wait_ready: bool = True) -> dict[str, Any]:
        # uploads stay on HTTP transport for now because package surface is inconsistent.
        return await self._http().upload_attachment(
            upload_type=upload_type,
            filename=filename,
            content=content,
            content_type=content_type,
            wait_ready=wait_ready,
        )

    async def download_bytes(self, location: str) -> bytes:
        return await self._http().download_bytes(location)
