from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.enums import Platform
from app.repositories.platform_settings_repo import PlatformSettingsRepo
from app.utils.crypto import SecretBox


def build_empty_platform_defaults() -> dict[str, dict[str, Any]]:
    return {
        Platform.TELEGRAM.value: {"config": {}, "secrets": {}},
        Platform.VK.value: {"config": {}, "secrets": {}},
        Platform.MAX.value: {"config": {}, "secrets": {}},
    }


async def load_platform_settings_from_db(
    session_factory: async_sessionmaker,
    secrets_encryption_key: str,
) -> dict[str, dict[str, Any]]:
    effective = build_empty_platform_defaults()
    async with session_factory() as session:
        repo = PlatformSettingsRepo(session, SecretBox(secrets_encryption_key))
        rows = await repo.list_all(include_secrets=True)

    for row in rows:
        platform = row["platform"]
        effective.setdefault(platform, {"config": {}, "secrets": {}})
        effective[platform]["config"].update(row.get("config") or {})
        effective[platform]["secrets"].update(row.get("secrets") or {})
    return effective


def build_platform_status(effective: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    tg = effective.get(Platform.TELEGRAM.value, {"config": {}, "secrets": {}})
    vk = effective.get(Platform.VK.value, {"config": {}, "secrets": {}})
    mx = effective.get(Platform.MAX.value, {"config": {}, "secrets": {}})
    return {
        "telegram": {
            "enabled": bool(tg["config"] or tg["secrets"]),
            "configured": bool(
                tg["config"].get("api_id")
                and tg["secrets"].get("api_hash")
                and (tg["secrets"].get("string_session") or tg["secrets"].get("bot_token"))
            ),
            "receive_updates": bool(tg["config"].get("receive_updates", True)),
            "mode": "user_session" if tg["secrets"].get("string_session") else ("bot_token" if tg["secrets"].get("bot_token") else "unconfigured"),
        },
        "vk": {
            "enabled": bool(vk["config"] or vk["secrets"]),
            "configured": bool(vk["secrets"].get("token") and vk["config"].get("group_id")),
            "receive_updates": bool(vk["config"].get("receive_updates", True)),
            "mode": "callback_api",
        },
        "max": {
            "enabled": bool(mx["config"] or mx["secrets"]),
            "configured": bool(mx["secrets"].get("token")),
            "receive_updates": bool(mx["config"].get("receive_updates", True)),
            "mode": "webhook",
        },
    }
