from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class VkApiError(RuntimeError):
    def __init__(self, *, method: str, error: dict[str, Any]) -> None:
        self.method = method
        self.error = error
        self.error_code = error.get("error_code")
        self.error_msg = str(error.get("error_msg") or "Unknown VK API error")
        super().__init__(f"VK API error for {method}: [{self.error_code}] {self.error_msg}")

    @property
    def is_auth_error(self) -> bool:
        return self.error_code == 5


class VkClient:
    def __init__(self, token: str, api_version: str = "5.199") -> None:
        self.token = token
        self.api_version = api_version
        self._api = None

    async def call_method(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(params or {})
        payload["access_token"] = self.token
        payload["v"] = self.api_version

        result = await self._call_with_vkbottle(method=method, params=payload)
        if result is not None:
            return result

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"https://api.vk.com/method/{method}", data=payload)
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            error = data["error"]
            raise VkApiError(method=method, error=error)
        return data["response"]

    async def upload_file(
        self,
        upload_url: str,
        *,
        form_field: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        files = {
            form_field: (filename, content, content_type or "application/octet-stream"),
        }
        data = extra_fields or {}
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(upload_url, data=data, files=files)
            response.raise_for_status()
            return response.json()

    async def download_bytes(self, location: str) -> bytes:
        if location.startswith("http://") or location.startswith("https://"):
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                response = await client.get(location)
                response.raise_for_status()
                return response.content
        return Path(location).read_bytes()

    async def get_group_long_poll_server(self, group_id: int) -> dict[str, Any]:
        return await self.call_method("groups.getLongPollServer", {"group_id": group_id})

    async def long_poll_once(
        self,
        *,
        server: str,
        key: str,
        ts: str | int,
        wait: int = 25,
    ) -> dict[str, Any]:
        params = {
            "act": "a_check",
            "key": key,
            "ts": ts,
            "wait": wait,
        }
        base_url = server if server.startswith(("http://", "https://")) else f"https://{server}"
        async with httpx.AsyncClient(timeout=wait + 15.0) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            return response.json()

    async def get_bot_long_poll_server(self, group_id: int) -> dict[str, Any]:
        data = await self.get_group_long_poll_server(group_id)
        server = data.get("server")
        if server and not str(server).startswith(("http://", "https://")):
            data["server"] = f"https://{server}"
        return data

    async def _call_with_vkbottle(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if self._api is None:
            self._api = self._build_vkbottle_api()
        if self._api is None:
            return None

        request_method = getattr(self._api, "request", None)
        if request_method is None:
            return None

        try:
            result = await request_method(method, params)
        except TypeError:
            return None
        except Exception:
            logger.exception("vkbottle API request failed, falling back to raw HTTP")
            return None

        if isinstance(result, dict) and "response" in result:
            return result["response"]
        if isinstance(result, dict):
            return result
        raw_result = getattr(result, "__dict__", None)
        if isinstance(raw_result, dict):
            return raw_result
        return None

    def _build_vkbottle_api(self):
        try:
            from vkbottle import API  # type: ignore
        except Exception:
            return None

        try:
            return API(token=self.token)
        except TypeError:
            try:
                return API(self.token)
            except Exception:
                logger.exception("Failed to initialize vkbottle API")
                return None
