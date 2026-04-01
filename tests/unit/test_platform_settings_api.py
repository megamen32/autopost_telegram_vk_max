import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_platform_settings_save_and_masked_response(tmp_path: Path):
    db_path = tmp_path / "platform_settings.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-platform-settings"

    from app.main import app

    with TestClient(app) as client:
        put_resp = client.put(
            "/api/platform-settings/telegram",
            json={
                "platform": "telegram",
                "config": {
                    "api_id": 12345,
                    "receive_updates": True,
                    "allowed_source_chat_ids": ["-1001", "-1002"],
                },
                "secrets": {
                    "api_hash": "hash123",
                    "bot_token": "bot:token",
                },
            },
        )
        assert put_resp.status_code == 200

        get_resp = client.get("/api/platform-settings/telegram")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["platform"] == "telegram"
        assert data["config"]["api_id"] == 12345
        assert data["secret_fields_present"]["api_hash"] is True
        assert data["secret_fields_present"]["bot_token"] is True
        assert "secrets" not in data
