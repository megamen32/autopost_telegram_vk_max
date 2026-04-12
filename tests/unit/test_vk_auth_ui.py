import asyncio
import os
import sys
import time
from types import SimpleNamespace
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.services.vk_oauth import (
    build_authorize_url,
    build_vk_oauth_group_authorize_url,
    compute_expires_at,
    is_token_expired,
    refresh_access_token,
)


def test_vk_auth_button_is_rendered_in_webui():
    html = Path("app/webui/index.html").read_text(encoding="utf-8")

    assert 'class="btn vk-auth-btn"' in html
    assert 'class="btn secondary vk-load-groups-btn"' in html
    assert "Legacy: токен сообщества" in html
    assert 'class="btn secondary vk-media-auth-btn"' not in html
    assert "@vkid/sdk@<3.0.0" not in html
    assert "document.currentScript.parentElement" not in html


def test_vk_authorize_url_has_expected_parameters():
    url = build_authorize_url(
        client_id="123456",
        redirect_uri="https://autopost.example/auth/vk/callback",
        state="state-abc",
        code_challenge="challenge-xyz",
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "id.vk.ru"
    assert parsed.path == "/authorize"
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["123456"]
    assert query["redirect_uri"] == ["https://autopost.example/auth/vk/callback"]
    assert query["state"] == ["state-abc"]
    assert query["code_challenge"] == ["challenge-xyz"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["vkid.personal_info photos video wall market groups"]


def test_vk_group_authorize_url_uses_implicit_flow():
    url = build_vk_oauth_group_authorize_url(
        client_id="123456",
        group_ids="123,456",
        redirect_uri="https://autopost.example/auth/vk/groups-callback",
        state="group-state-abc",
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "oauth.vk.com"
    assert parsed.path == "/authorize"
    assert query["client_id"] == ["123456"]
    assert query["group_ids"] == ["123,456"]
    assert query["redirect_uri"] == ["https://autopost.example/auth/vk/groups-callback"]
    assert query["response_type"] == ["token"]
    assert query["v"] == ["5.199"]
    assert query["display"] == ["popup"]
    assert query["scope"] == ["manage,photos"]
    assert query["state"] == ["group-state-abc"]


def test_vk_refresh_access_token_posts_expected_payload(monkeypatch):
    calls: list[dict] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "new-token", "refresh_token": "new-refresh", "expires_in": 3600}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, data):
            calls.append({"url": url, "data": data})
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.vk_oauth.httpx",
        SimpleNamespace(AsyncClient=lambda *args, **kwargs: FakeClient()),
    )

    response = asyncio.run(
        refresh_access_token(
            client_id="123456",
            refresh_token="refresh-123",
            device_id="device-123",
            scope="photos wall",
            state="refresh-state",
        )
    )

    assert response["access_token"] == "new-token"
    assert calls == [
        {
            "url": "https://id.vk.ru/oauth2/auth",
            "data": {
                "grant_type": "refresh_token",
                "client_id": "123456",
                "refresh_token": "refresh-123",
                "device_id": "device-123",
                "scope": "photos wall",
                "state": "refresh-state",
            },
        }
    ]


def test_vk_token_expiry_helpers():
    issued_at = int(time.time())
    expires_at = compute_expires_at(120, issued_at=issued_at)

    assert expires_at == issued_at + 120
    assert is_token_expired(expires_at, leeway_seconds=0) is False
    assert is_token_expired(1, leeway_seconds=0) is True


def test_vk_shared_callback_page_supports_group_finalizer_only(tmp_path):
    db_path = tmp_path / "vk_callback_ui.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-vk-callback-ui"
    os.environ["DEBUG"] = "false"

    sys.modules.pop("app.main", None)
    from app.main import app

    try:
        with TestClient(app) as client:
            response = client.get("/auth/vk/callback")
            assert response.status_code == 200
            assert "/api/auth/vk/groups-finalize" in response.text
            assert "access_token_" in response.text
            assert "/api/auth/vk/media-finalize" not in response.text
    finally:
        sys.modules.pop("app.main", None)
