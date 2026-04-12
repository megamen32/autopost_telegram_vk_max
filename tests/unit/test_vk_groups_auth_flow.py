import asyncio
import os
import sys
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.repositories.adapter_instances_repo import AdapterInstancesRepo
from app.utils.crypto import SecretBox


def test_vk_groups_auth_flow_persists_group_token(tmp_path):
    db_path = tmp_path / "vk_groups_auth.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-vk-groups-auth"
    os.environ["DEBUG"] = "false"

    sys.modules.pop("app.main", None)
    from app.main import app

    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/adapter-instances",
                json={
                    "id": "vk-test-instance",
                    "adapter_key": "vk",
                    "display_name": "VK test",
                    "enabled": True,
                    "config": {
                        "group_id": 12345,
                        "vk_id_client_id": "client-123",
                    },
                    "secrets": {},
                },
            )
            assert create_resp.status_code == 200

            start_resp = client.post(
                "/api/auth/vk/groups-auth-start",
                json={
                    "instance_id": "vk-test-instance",
                    "group_ids": "67890,12345",
                },
            )
            assert start_resp.status_code == 200
            start_data = start_resp.json()
            parsed = urlparse(start_data["authorize_url"])
            query = parse_qs(parsed.query)
            assert query["response_type"] == ["token"]
            assert query["group_ids"] == ["67890,12345"]
            assert query["redirect_uri"][0].endswith("/auth/vk/callback")

            finalize_resp = client.post(
                "/api/auth/vk/groups-finalize",
                json={
                    "state": start_data["state"],
                    "tokens": {"67890": "group-access-token-67890", "12345": "group-access-token-12345"},
                },
            )
            assert finalize_resp.status_code == 200
            assert finalize_resp.json()["ok"] is True

            instances_resp = client.get("/api/adapter-instances")
            assert instances_resp.status_code == 200
            instances = instances_resp.json()
            instance = next(item for item in instances if item["id"] == "vk-test-instance")
            assert instance["config"]["vk_oauth_group_ids"] == "67890,12345"
            assert instance["secret_fields_present"]["token"] is True

            async def read_instance():
                async with client.app.state.session_factory() as session:
                    repo = AdapterInstancesRepo(session, SecretBox("test-key-for-vk-groups-auth"))
                    return await repo.get("vk-test-instance", include_secrets=True)

            stored = asyncio.run(read_instance())
            assert stored["secrets"]["token"] == "group-access-token-12345"
    finally:
        sys.modules.pop("app.main", None)


def test_vk_groups_scope_auth_flow_persists_admin_groups_token(monkeypatch, tmp_path):
    db_path = tmp_path / "vk_groups_scope_auth.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-vk-groups-scope-auth"
    os.environ["DEBUG"] = "false"

    sys.modules.pop("app.main", None)
    from app.main import app

    async def fake_exchange_code_for_token(**kwargs):
        return {
            "access_token": "vk-groups-scope-token",
            "user_id": 46887791,
            "expires_in": 3600,
        }

    monkeypatch.setattr("app.api.vk_auth.exchange_code_for_token", fake_exchange_code_for_token)

    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/adapter-instances",
                json={
                    "id": "vk-groups-scope-instance",
                    "adapter_key": "vk",
                    "display_name": "VK groups scope test",
                    "enabled": True,
                    "config": {
                        "group_id": 12345,
                        "vk_id_client_id": "client-123",
                    },
                    "secrets": {},
                },
            )
            assert create_resp.status_code == 200

            start_resp = client.post(
                "/api/auth/vk/groups-scope-start",
                json={"instance_id": "vk-groups-scope-instance"},
            )
            assert start_resp.status_code == 200
            start_data = start_resp.json()
            parsed = urlparse(start_data["authorize_url"])
            query = parse_qs(parsed.query)
            assert query["response_type"] == ["code"]
            assert query["scope"] == ["groups"]
            assert query["redirect_uri"][0].endswith("/auth/vk/callback")

            callback_resp = client.get(
                "/auth/vk/callback",
                params={
                    "code": "vk-code-123",
                    "state": start_data["state"],
                    "device_id": "device-123",
                },
            )
            assert callback_resp.status_code == 200
            assert "VK groups scope подключён" in callback_resp.text

            instances_resp = client.get("/api/adapter-instances")
            assert instances_resp.status_code == 200
            instances = instances_resp.json()
            instance = next(item for item in instances if item["id"] == "vk-groups-scope-instance")
            assert instance["config"]["vk_groups_oauth_user_id"] == 46887791
            assert instance["config"]["vk_groups_oauth_scope"] == "groups"
            assert instance["config"]["vk_groups_token_expires_at"] > 0
            assert instance["secret_fields_present"]["vk_groups_access_token"] is True

            async def read_instance():
                async with client.app.state.session_factory() as session:
                    repo = AdapterInstancesRepo(session, SecretBox("test-key-for-vk-groups-scope-auth"))
                    return await repo.get("vk-groups-scope-instance", include_secrets=True)

            stored = asyncio.run(read_instance())
            assert stored["secrets"]["vk_groups_access_token"] == "vk-groups-scope-token"
    finally:
        sys.modules.pop("app.main", None)


def test_vk_media_auth_start_uses_vk_id_code_flow(tmp_path):
    db_path = tmp_path / "vk_media_auth.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-vk-media-auth"
    os.environ["DEBUG"] = "false"

    sys.modules.pop("app.main", None)
    from app.main import app

    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/adapter-instances",
                json={
                    "id": "vk-media-instance",
                    "adapter_key": "vk",
                    "display_name": "VK media test",
                    "enabled": True,
                    "config": {
                        "group_id": 12345,
                        "vk_id_client_id": "client-123",
                    },
                    "secrets": {},
                },
            )
            assert create_resp.status_code == 200

            start_resp = client.post(
                "/api/auth/vk/media-start",
                json={"instance_id": "vk-media-instance"},
            )
            assert start_resp.status_code == 200
            start_data = start_resp.json()
            parsed = urlparse(start_data["authorize_url"])
            query = parse_qs(parsed.query)
            assert query["response_type"] == ["code"]
            assert query["scope"] == ["vkid.personal_info photos video wall market groups"]
            assert query["code_challenge_method"] == ["S256"]
            assert query["redirect_uri"][0].endswith("/auth/vk/callback")
    finally:
        sys.modules.pop("app.main", None)


def test_vk_auth_callback_persists_refresh_metadata(monkeypatch, tmp_path):
    db_path = tmp_path / "vk_auth_callback.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-vk-auth-callback"
    os.environ["DEBUG"] = "false"

    sys.modules.pop("app.main", None)
    from app.main import app

    async def fake_exchange_code_for_token(**kwargs):
        return {
            "access_token": "vk-user-access-token",
            "refresh_token": "vk-refresh-token",
            "id_token": "vk-id-token",
            "user_id": 777,
            "expires_in": 1800,
        }

    monkeypatch.setattr("app.api.vk_auth.exchange_code_for_token", fake_exchange_code_for_token)

    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/adapter-instances",
                json={
                    "id": "vk-auth-instance",
                    "adapter_key": "vk",
                    "display_name": "VK auth test",
                    "enabled": True,
                    "config": {
                        "group_id": 12345,
                        "vk_id_client_id": "client-123",
                    },
                    "secrets": {},
                },
            )
            assert create_resp.status_code == 200

            start_resp = client.post("/api/auth/vk/start", json={"instance_id": "vk-auth-instance"})
            assert start_resp.status_code == 200
            start_data = start_resp.json()

            callback_resp = client.get(
                "/auth/vk/callback",
                params={
                    "code": "vk-code-777",
                    "state": start_data["state"],
                    "device_id": "device-777",
                },
            )
            assert callback_resp.status_code == 200
            assert "VK подключён" in callback_resp.text

            instances_resp = client.get("/api/adapter-instances")
            assert instances_resp.status_code == 200
            instances = instances_resp.json()
            instance = next(item for item in instances if item["id"] == "vk-auth-instance")
            assert instance["config"]["vk_oauth_user_id"] == 777
            assert instance["config"]["vk_oauth_scope"] == "vkid.personal_info photos video wall market groups"
            assert instance["config"]["vk_oauth_token_expires_at"] > 0
            assert instance["secret_fields_present"]["user_access_token_for_media"] is True
            assert instance["secret_fields_present"]["vk_oauth_refresh_token"] is True

            async def read_instance():
                async with client.app.state.session_factory() as session:
                    repo = AdapterInstancesRepo(session, SecretBox("test-key-for-vk-auth-callback"))
                    return await repo.get("vk-auth-instance", include_secrets=True)

            stored = asyncio.run(read_instance())
            assert stored["secrets"]["user_access_token_for_media"] == "vk-user-access-token"
            assert stored["secrets"]["vk_oauth_access_token"] == "vk-user-access-token"
            assert stored["secrets"]["vk_oauth_refresh_token"] == "vk-refresh-token"
            assert stored["secrets"]["vk_oauth_device_id"] == "device-777"
    finally:
        sys.modules.pop("app.main", None)
