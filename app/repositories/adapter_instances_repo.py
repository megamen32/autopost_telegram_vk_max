from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, select

from app.db.models import AdapterInstanceORM
from app.repositories.base import SQLAlchemyRepo
from app.utils.crypto import SecretBox


class AdapterInstancesRepo(SQLAlchemyRepo):
    def __init__(self, session, secret_box: SecretBox) -> None:
        super().__init__(session)
        self.secret_box = secret_box

    async def list_all(self, include_secrets: bool = False) -> list[dict[str, Any]]:
        rows = (await self.session.execute(select(AdapterInstanceORM).order_by(AdapterInstanceORM.created_at, AdapterInstanceORM.id))).scalars().all()
        return [self._to_dict(row, include_secrets=include_secrets) for row in rows]

    async def get(self, instance_id: str, include_secrets: bool = False) -> dict[str, Any] | None:
        row = await self.session.get(AdapterInstanceORM, instance_id)
        return self._to_dict(row, include_secrets=include_secrets) if row else None

    async def upsert(self, *, instance_id: str, adapter_key: str, platform: str, display_name: str, enabled: bool, config: dict[str, Any], secret_updates: dict[str, Any] | None = None) -> dict[str, Any]:
        row = await self.session.get(AdapterInstanceORM, instance_id)
        if row is None:
            row = AdapterInstanceORM(id=instance_id, adapter_key=adapter_key, platform=platform, display_name=display_name, enabled=enabled, config_json='{}')
            self.session.add(row)
        row.adapter_key = adapter_key
        row.platform = platform
        row.display_name = display_name
        row.enabled = enabled
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

    async def delete(self, instance_id: str) -> bool:
        result = await self.session.execute(delete(AdapterInstanceORM).where(AdapterInstanceORM.id == instance_id))
        await self.session.commit()
        return (result.rowcount or 0) > 0

    def _to_dict(self, row: AdapterInstanceORM, include_secrets: bool) -> dict[str, Any]:
        config = self._loads_json(row.config_json)
        secrets = self.secret_box.decrypt_json(row.secrets_encrypted)
        payload = {
            'id': row.id,
            'adapter_key': row.adapter_key,
            'platform': row.platform,
            'display_name': row.display_name,
            'enabled': row.enabled,
            'config': config,
            'secret_fields_present': {key: True for key in secrets.keys()},
            'updated_at': row.updated_at.isoformat() if row.updated_at else None,
        }
        if include_secrets:
            payload['secrets'] = secrets
        return payload

    @staticmethod
    def _loads_json(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        return json.loads(value)
