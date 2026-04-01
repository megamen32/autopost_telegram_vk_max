import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_dashboard_index_available(tmp_path: Path):
    db_path = tmp_path / "dashboard.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Autopost Sync Control Panel" in response.text


def test_dashboard_overview_json(tmp_path: Path):
    db_path = tmp_path / "dashboard_overview.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()
        assert "platform_status" in data
        assert set(data["platform_status"].keys()) == {"telegram", "vk", "max"}
