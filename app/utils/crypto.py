from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class SecretBox:
    def __init__(self, raw_key: str) -> None:
        self._fernet = Fernet(self._normalize_key(raw_key))

    @staticmethod
    def _normalize_key(raw_key: str) -> bytes:
        raw = raw_key.strip().encode("utf-8")
        try:
            Fernet(raw)
            return raw
        except Exception:
            digest = hashlib.sha256(raw).digest()
            return base64.urlsafe_b64encode(digest)

    def encrypt_json(self, value: dict[str, Any]) -> str:
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return self._fernet.encrypt(payload).decode("utf-8")

    def decrypt_json(self, token: str | None) -> dict[str, Any]:
        if not token:
            return {}
        try:
            payload = self._fernet.decrypt(token.encode("utf-8"))
        except InvalidToken as exc:
            raise ValueError("Failed to decrypt platform secrets. Check SECRETS_ENCRYPTION_KEY.") from exc
        return json.loads(payload.decode("utf-8"))
