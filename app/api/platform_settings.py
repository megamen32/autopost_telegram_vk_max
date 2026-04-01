from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_container, get_session
from app.domain.enums import Platform
from app.repositories.platform_settings_repo import PlatformSettingsRepo
from app.schemas.api import PlatformSettingsResponseSchema, PlatformSettingsUpdateSchema
from app.services.platform_settings_service import build_empty_platform_defaults, build_platform_status, load_platform_settings_from_db
from app.utils.crypto import SecretBox

router = APIRouter(prefix="/api/platform-settings", tags=["platform-settings"])


@router.get("")
async def list_platform_settings(session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    defaults = build_empty_platform_defaults()
    repo = PlatformSettingsRepo(session, SecretBox(settings.secrets_encryption_key))
    rows = {row["platform"]: row for row in await repo.list_all(include_secrets=False)}

    result = []
    for platform in Platform:
        platform_key = platform.value
        stored = rows.get(platform_key)
        result.append(
            PlatformSettingsResponseSchema(
                platform=platform,
                config=(defaults.get(platform_key, {}).get("config") or {}) | ((stored or {}).get("config") or {}),
                secret_fields_present=(stored or {}).get("secret_fields_present") or {},
                updated_at=(stored or {}).get("updated_at"),
            )
        )
    return result


@router.get("/status/effective")
async def effective_platform_status(container=Depends(get_container)):
    settings = get_settings()
    effective = await load_platform_settings_from_db(container.session_factory, settings.secrets_encryption_key)
    return {
        "platform_status": build_platform_status(effective),
        "effective": {
            platform: {
                "config": values.get("config") or {},
                "secret_fields_present": {key: True for key, value in (values.get("secrets") or {}).items() if value not in (None, "")},
            }
            for platform, values in effective.items()
        },
        "note": "Platform settings are loaded only from the database. Environment variables are infrastructure-only and do not affect Telegram/VK/MAX runtime config.",
    }


@router.get("/{platform}")
async def get_platform_settings(platform: Platform, session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    repo = PlatformSettingsRepo(session, SecretBox(settings.secrets_encryption_key))
    stored = await repo.get(platform, include_secrets=False)
    return PlatformSettingsResponseSchema(
        platform=platform,
        config=((stored or {}).get("config") or {}),
        secret_fields_present=(stored or {}).get("secret_fields_present") or {},
        updated_at=(stored or {}).get("updated_at"),
    )


@router.put("/{platform}")
async def upsert_platform_settings(
    platform: Platform,
    payload: PlatformSettingsUpdateSchema,
    session: AsyncSession = Depends(get_session),
):
    settings = get_settings()
    repo = PlatformSettingsRepo(session, SecretBox(settings.secrets_encryption_key))
    row = await repo.upsert(platform=platform, config=payload.config, secret_updates=payload.secrets)
    return row
