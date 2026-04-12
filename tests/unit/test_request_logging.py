import os
import sys

from fastapi.testclient import TestClient


def test_request_logging_captures_json_body_and_query_params(caplog, tmp_path):
    db_path = tmp_path / "request_logging.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["SECRETS_ENCRYPTION_KEY"] = "test-key-for-request-logging"
    os.environ["DEBUG"] = "false"

    sys.modules.pop("app.main", None)
    from app.main import app

    caplog.set_level("INFO", logger="autopost_sync.request")

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/vk/groups?trace=1&code=oauth-code-123&state=oauth-state-123&device_id=device-123",
                json={
                    "instance_id": "missing-instance",
                    "access_token": "should-be-redacted",
                    "tokens": {"12345": "group-token-123"},
                },
            )
            assert response.status_code == 404

        messages = [record.getMessage() for record in caplog.records if record.name == "autopost_sync.request"]
        assert any("incoming request" in message for message in messages)
        assert any("request completed" in message for message in messages)
        assert any('"path": "/api/auth/vk/groups"' in message for message in messages)
        assert any('"trace": "1"' in message for message in messages)
        assert any('"code": "[redacted]"' in message for message in messages)
        assert any('"state": "[redacted]"' in message for message in messages)
        assert any('"device_id": "[redacted]"' in message for message in messages)
        assert any('"instance_id": "missing-instance"' in message for message in messages)
        assert any('"access_token": "[redacted]"' in message for message in messages)
        assert any('"tokens": "[redacted]"' in message for message in messages)
    finally:
        sys.modules.pop("app.main", None)
