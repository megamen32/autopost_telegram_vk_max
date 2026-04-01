from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class VkApiError(RuntimeError):
    pass


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
            raise VkApiError(f"VK API error for {method}: {error}")
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
