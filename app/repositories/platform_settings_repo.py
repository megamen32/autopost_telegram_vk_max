from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.db.models import PlatformSettingORM
from app.domain.enums import Platform
from app.repositories.base import SQLAlchemyRepo
from app.utils.crypto import SecretBox


class PlatformSettingsRepo(SQLAlchemyRepo):
    def __init__(self, session, secret_box: SecretBox) -> None:
        super().__init__(session)
        self.secret_box = secret_box

    async def get(self, platform: Platform | str, include_secrets: bool = False) -> dict[str, Any] | None:
        platform_value = platform.value if isinstance(platform, Platform) else platform
        row = await self.session.get(PlatformSettingORM, platform_value)
        if row is None:
            return None
        return self._to_dict(row, include_secrets=include_secrets)

    async def list_all(self, include_secrets: bool = False) -> list[dict[str, Any]]:
        rows = (await self.session.execute(select(PlatformSettingORM).order_by(PlatformSettingORM.platform))).scalars().all()
        return [self._to_dict(row, include_secrets=include_secrets) for row in rows]

    async def upsert(
        self,
        platform: Platform,
        config: dict[str, Any],
        secret_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = await self.session.get(PlatformSettingORM, platform.value)
        if row is None:
            row = PlatformSettingORM(platform=platform.value, config_json="{}", secrets_encrypted=None)
            self.session.add(row)

        current_config = self._loads_json(row.config_json)
        current_config.update(config)
        row.config_json = json.dumps(current_config, ensure_ascii=False, separators=(",", ":"))

        current_secrets = self.secret_box.decrypt_json(row.secrets_encrypted)
        if secret_updates:
            for key, value in secret_updates.items():
                if value in (None, ""):
                    current_secrets.pop(key, None)
                else:
                    current_secrets[key] = value
        row.secrets_encrypted = self.secret_box.encrypt_json(current_secrets) if current_secrets else None

        await self.session.commit()
        await self.session.refresh(row)
        return self._to_dict(row, include_secrets=False)

    def _to_dict(self, row: PlatformSettingORM, include_secrets: bool) -> dict[str, Any]:
        config = self._loads_json(row.config_json)
        secrets = self.secret_box.decrypt_json(row.secrets_encrypted)
        payload = {
            "platform": row.platform,
            "config": config,
            "secret_fields_present": {key: True for key in secrets.keys()},
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        if include_secrets:
            payload["secrets"] = secrets
        return payload

    @staticmethod
    def _loads_json(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        return json.loads(value)
