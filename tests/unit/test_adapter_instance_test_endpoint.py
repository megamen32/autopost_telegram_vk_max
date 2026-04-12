from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient


class _FakeAdapter:
    def __init__(self) -> None:
        self.startup_called = False
        self.shutdown_called = False
        self.enabled = True

    async def startup(self, on_post=None) -> None:
        self.startup_called = True

    async def shutdown(self) -> None:
        self.shutdown_called = True


class _FakeRegistry:
    def __init__(self, adapter: _FakeAdapter) -> None:
        self.adapter = adapter

    def create_adapter(self, adapter_key, instance_id, config, secrets):
        return self.adapter


def test_adapter_instance_test_endpoint_runs_startup_and_shutdown(tmp_path: Path):
    db_path = tmp_path / "adapter_instance_test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-adapter-test"

    from app.dependencies import get_container
    from app.main import app

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/adapter-instances",
            json={
                "adapter_key": "telegram",
                "display_name": "Smoke TG",
                "enabled": True,
                "config": {},
                "secrets": {},
            },
        )
        assert create_resp.status_code == 200
        instance_id = create_resp.json()["id"]

        fake_adapter = _FakeAdapter()
        fake_container = SimpleNamespace(
            secrets_encryption_key="test-key-for-adapter-test",
            definition_registry=_FakeRegistry(fake_adapter),
        )
        app.dependency_overrides[get_container] = lambda: fake_container
        try:
            resp = client.post(f"/api/adapter-instances/{instance_id}/test")
        finally:
            app.dependency_overrides.pop(get_container, None)

        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert fake_adapter.startup_called is True
        assert fake_adapter.shutdown_called is True
