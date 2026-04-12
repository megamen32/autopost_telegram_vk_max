from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from threading import Lock
from urllib.parse import urlencode

import httpx

VK_ID_AUTHORIZE_URL = "https://id.vk.ru/authorize"
VK_ID_TOKEN_URL = "https://id.vk.ru/oauth2/auth"
VK_ID_REVOKE_URL = "https://id.vk.ru/oauth2/revoke"
VK_ID_LOGOUT_URL = "https://id.vk.ru/oauth2/logout"
VK_ID_DEFAULT_SCOPE = "vkid.personal_info photos video wall market groups"
VK_ID_GROUPS_SCOPE = "groups"


@dataclass(slots=True)
class VkOAuthSession:
    state: str
    code_verifier: str
    created_at: float
    adapter_instance_id: str
    redirect_uri: str
    client_id: str
    purpose: str
    scope: str = VK_ID_DEFAULT_SCOPE


class VkOAuthStore:
    def __init__(self) -> None:
        self._items: dict[str, VkOAuthSession] = {}
        self._lock = Lock()

    def create(
        self,
        *,
        adapter_instance_id: str,
        redirect_uri: str,
        client_id: str,
        scope: str = VK_ID_DEFAULT_SCOPE,
        purpose: str = "profile",
    ) -> VkOAuthSession:
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        session = VkOAuthSession(
            state=state,
            code_verifier=code_verifier,
            created_at=time.time(),
            adapter_instance_id=adapter_instance_id,
            redirect_uri=redirect_uri,
            client_id=client_id,
            purpose=purpose,
            scope=scope,
        )
        with self._lock:
            self._items[state] = session
        return session

    def pop(self, state: str) -> VkOAuthSession | None:
        with self._lock:
            return self._items.pop(state, None)


@dataclass(slots=True)
class VkGroupOAuthSession:
    state: str
    created_at: float
    adapter_instance_id: str
    redirect_uri: str
    client_id: str
    group_ids: str


class VkGroupOAuthStore:
    def __init__(self) -> None:
        self._items: dict[str, VkGroupOAuthSession] = {}
        self._lock = Lock()

    def create(self, *, adapter_instance_id: str, redirect_uri: str, client_id: str, group_ids: str) -> VkGroupOAuthSession:
        state = secrets.token_urlsafe(32)
        session = VkGroupOAuthSession(
            state=state,
            created_at=time.time(),
            adapter_instance_id=adapter_instance_id,
            redirect_uri=redirect_uri,
            client_id=client_id,
            group_ids=group_ids,
        )
        with self._lock:
            self._items[state] = session
        return session

    def pop(self, state: str) -> VkGroupOAuthSession | None:
        with self._lock:
            return self._items.pop(state, None)


def build_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def build_authorize_url(*, client_id: str, redirect_uri: str, state: str, code_challenge: str, scope: str = VK_ID_DEFAULT_SCOPE) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{VK_ID_AUTHORIZE_URL}?{query}"


def extract_callback_payload(query_params: dict[str, str]) -> dict[str, str | None]:
    payload_raw = query_params.get("payload")
    if payload_raw:
        try:
            payload = json.loads(payload_raw)
            return {
                "code": payload.get("code"),
                "state": payload.get("state"),
                "device_id": payload.get("device_id"),
            }
        except Exception:
            pass
    return {
        "code": query_params.get("code"),
        "state": query_params.get("state"),
        "device_id": query_params.get("device_id"),
    }


async def exchange_code_for_token(*, client_id: str, code: str, code_verifier: str, device_id: str, redirect_uri: str, state: str | None = None) -> dict:
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "code_verifier": code_verifier,
        "device_id": device_id,
        "redirect_uri": redirect_uri,
    }
    if state:
        data["state"] = state
    return await _request_tokens(data)


async def refresh_access_token(
    *,
    client_id: str,
    refresh_token: str,
    device_id: str,
    scope: str | None = None,
    state: str | None = None,
) -> dict:
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
        "device_id": device_id,
    }
    if scope:
        data["scope"] = scope
    if state:
        data["state"] = state
    return await _request_tokens(data)


async def _request_tokens(data: dict[str, str]) -> dict:
    return await _post_vk_id_form(VK_ID_TOKEN_URL, data)


async def revoke_access_token(
    *,
    client_id: str,
    access_token: str,
    device_id: str | None = None,
    state: str | None = None,
) -> dict:
    data: dict[str, str] = {
        "client_id": client_id,
        "access_token": access_token,
    }
    if device_id:
        data["device_id"] = device_id
    if state:
        data["state"] = state
    return await _post_vk_id_form(VK_ID_REVOKE_URL, data)


async def logout_access_token(
    *,
    client_id: str,
    access_token: str,
    device_id: str | None = None,
    state: str | None = None,
) -> dict:
    data: dict[str, str] = {
        "client_id": client_id,
        "access_token": access_token,
    }
    if device_id:
        data["device_id"] = device_id
    if state:
        data["state"] = state
    return await _post_vk_id_form(VK_ID_LOGOUT_URL, data)


async def _post_vk_id_form(url: str, data: dict[str, str]) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=data)
        resp.raise_for_status()
        return resp.json()


def compute_expires_at(expires_in: int | str | None, *, issued_at: float | None = None) -> int | None:
    if expires_in in (None, ""):
        return None
    try:
        expires_in_value = int(expires_in)
    except (TypeError, ValueError):
        return None
    if expires_in_value <= 0:
        return None
    base_ts = int(issued_at or time.time())
    return base_ts + expires_in_value


def is_token_expired(expires_at: int | float | str | None, *, leeway_seconds: int = 60) -> bool:
    if expires_at in (None, ""):
        return False
    try:
        expires_at_value = int(float(expires_at))
    except (TypeError, ValueError):
        return False
    return time.time() >= (expires_at_value - max(leeway_seconds, 0))


VK_OAUTH_AUTHORIZE_URL = "https://oauth.vk.com/authorize"
VK_OAUTH_GROUP_SCOPES = "manage,photos"


def build_vk_oauth_group_authorize_url(*, client_id: str, group_ids: str, redirect_uri: str, state: str | None = None) -> str:
    """Build Implicit Flow authorization URL for VK OAuth (group access token)."""
    return build_vk_oauth_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        scope=VK_OAUTH_GROUP_SCOPES,
        extra_params={"group_ids": group_ids},
    )


def build_vk_oauth_authorize_url(
    *,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str | None = None,
    display: str = "popup",
    extra_params: dict[str, str] | None = None,
) -> str:
    query = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "response_type": "token",
        "v": "5.199",
        "state": state or "",
        "display": display,
    }
    if extra_params:
        query.update(extra_params)
    return f"{VK_OAUTH_AUTHORIZE_URL}?{urlencode(query)}"


vk_oauth_store = VkOAuthStore()
vk_group_oauth_store = VkGroupOAuthStore()
