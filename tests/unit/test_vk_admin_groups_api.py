import os
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_vk_admin_groups_endpoint_parses_vk_response(monkeypatch, tmp_path):
    db_path = tmp_path / "vk_admin_groups.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-vk-admin-groups"
    os.environ["DEBUG"] = "false"

    sys.modules.pop("app.main", None)
    from app.main import app

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": {
                    "count": 2,
                    "items": [
                        {"id": 456, "name": "Beta", "screen_name": "beta"},
                        {"id": 123, "name": "Alpha", "screen_name": "alpha"},
                    ],
                }
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=lambda *args, **kwargs: FakeClient()))

    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/adapter-instances",
                json={
                    "id": "vk-admin-groups-instance",
                    "adapter_key": "vk",
                    "display_name": "VK admin groups",
                    "enabled": True,
                    "config": {
                        "group_id": 123,
                        "vk_id_client_id": "client-123",
                    },
                    "secrets": {
                        "vk_groups_access_token": "vk-user-token",
                    },
                },
            )
            assert create_resp.status_code == 200

            resp = client.post("/api/auth/vk/groups", json={"instance_id": "vk-admin-groups-instance"})
            assert resp.status_code == 200
            assert resp.json()["groups"] == [
                {"id": 123, "name": "Alpha", "screen_name": "alpha"},
                {"id": 456, "name": "Beta", "screen_name": "beta"},
            ]
    finally:
        sys.modules.pop("app.main", None)


def test_vk_admin_groups_endpoint_retries_transient_token_check_error(monkeypatch, tmp_path):
    db_path = tmp_path / "vk_admin_groups_retry.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-vk-admin-groups-retry"
    os.environ["DEBUG"] = "false"

    sys.modules.pop("app.main", None)
    from app.main import app

    calls = {"count": 0}

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] < 3:
                return FakeResponse(
                    {
                        "error": {
                            "error_code": 10,
                            "error_msg": "Internal server error: could not check access_token now, check later.",
                        }
                    }
                )
            return FakeResponse(
                {
                    "response": {
                        "count": 1,
                        "items": [
                            {"id": 123, "name": "Alpha", "screen_name": "alpha"},
                        ],
                    }
                }
            )

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=lambda *args, **kwargs: FakeClient()))

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr("app.api.vk_auth.asyncio.sleep", fake_sleep)

    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/adapter-instances",
                json={
                    "id": "vk-admin-groups-retry-instance",
                    "adapter_key": "vk",
                    "display_name": "VK admin groups retry",
                    "enabled": True,
                    "config": {
                        "group_id": 123,
                        "vk_id_client_id": "client-123",
                    },
                    "secrets": {
                        "vk_oauth_access_token": "vk-user-token",
                    },
                },
            )
            assert create_resp.status_code == 200

            resp = client.post("/api/auth/vk/groups", json={"instance_id": "vk-admin-groups-retry-instance"})
            assert resp.status_code == 200
            assert resp.json()["groups"] == [
                {"id": 123, "name": "Alpha", "screen_name": "alpha"},
            ]
            assert calls["count"] == 3
    finally:
        sys.modules.pop("app.main", None)


def test_vk_admin_groups_endpoint_returns_400_for_non_transient_vk_error(monkeypatch, tmp_path):
    db_path = tmp_path / "vk_admin_groups_error.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-vk-admin-groups-error"
    os.environ["DEBUG"] = "false"

    sys.modules.pop("app.main", None)
    from app.main import app

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "error": {
                    "error_code": 15,
                    "error_msg": "Access denied",
                }
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=lambda *args, **kwargs: FakeClient()))

    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/adapter-instances",
                json={
                    "id": "vk-admin-groups-error-instance",
                    "adapter_key": "vk",
                    "display_name": "VK admin groups error",
                    "enabled": True,
                    "config": {
                        "group_id": 123,
                        "vk_id_client_id": "client-123",
                    },
                    "secrets": {
                        "vk_oauth_access_token": "vk-user-token",
                    },
                },
            )
            assert create_resp.status_code == 200

            resp = client.post("/api/auth/vk/groups", json={"instance_id": "vk-admin-groups-error-instance"})
            assert resp.status_code == 400
            assert resp.json()["detail"] == "VK API error: Access denied"
    finally:
        sys.modules.pop("app.main", None)
