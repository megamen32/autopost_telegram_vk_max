import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_platform_runtime_config_comes_only_from_db(tmp_path: Path):
    db_path = tmp_path / "db_only_settings.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-db-only-settings"

    # Legacy platform env vars should not affect runtime config anymore.
    os.environ["TELEGRAM_API_ID"] = "99999"
    os.environ["TELEGRAM_API_HASH"] = "legacy-hash"
    os.environ["TELEGRAM_BOT_TOKEN"] = "legacy-bot-token"

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/platform-settings/status/effective")
        assert response.status_code == 200
        data = response.json()
        assert data["platform_status"]["telegram"]["configured"] is False
        assert data["effective"]["telegram"]["config"] == {}
        assert data["effective"]["telegram"]["secret_fields_present"] == {}
