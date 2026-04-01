from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx


class MaxApiError(RuntimeError):
    pass


class MaxClient:
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
