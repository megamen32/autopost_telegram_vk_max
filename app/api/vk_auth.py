from __future__ import annotations

import asyncio
import json
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_container, get_session
from app.repositories.adapter_instances_repo import AdapterInstancesRepo
from app.services.vk_oauth import (
    VK_ID_DEFAULT_SCOPE,
    build_authorize_url,
    build_code_challenge,
    build_vk_oauth_group_authorize_url,
    compute_expires_at,
    exchange_code_for_token,
    extract_callback_payload,
    VK_ID_GROUPS_SCOPE,
    vk_group_oauth_store,
    vk_oauth_store,
)
from app.services.vk_oauth_pages import build_vk_auth_success_page, build_vk_implicit_callback_page
from app.utils.crypto import SecretBox
from app.utils.logging import get_logger


router = APIRouter(tags=["vk_auth"])
logger = get_logger("autopost_sync.app")
_VK_TRANSIENT_TOKEN_CHECK_ERROR = "could not check access_token now, check later"


async def _load_vk_instance(
    *,
    instance_id: str,
    session: AsyncSession,
    container,
) -> tuple[AdapterInstancesRepo, dict]:
    repo = AdapterInstancesRepo(session, SecretBox(container.secrets_encryption_key))
    instance = await repo.get(instance_id, include_secrets=True)
    if not instance:
        raise HTTPException(status_code=404, detail="Adapter instance not found")
    if instance["adapter_key"] != "vk":
        raise HTTPException(status_code=400, detail="VK auth is only available for vk adapters")
    return repo, instance


def _require_vk_client_id(instance: dict) -> str:
    client_id = str((instance.get("config") or {}).get("vk_id_client_id") or "").strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="Укажи VK ID Client ID в advanced-настройках VK")
    return client_id


def _vk_admin_group_token_candidates(instance: dict) -> list[str]:
    secrets = instance.get("secrets") or {}
    candidates: list[str] = []
    for token in (
        secrets.get("vk_oauth_access_token"),
        secrets.get("user_access_token_for_media"),
        secrets.get("vk_groups_access_token"),
    ):
        token_value = str(token or "").strip()
        if token_value and token_value not in candidates:
            candidates.append(token_value)
    return candidates


def _is_vk_transient_token_check_error(error: dict) -> bool:
    error_msg = str(error.get("error_msg") or "").lower()
    return _VK_TRANSIENT_TOKEN_CHECK_ERROR in error_msg


async def _start_vk_id_oauth(
    *,
    instance_id: str,
    session: AsyncSession,
    container,
    scope: str,
    purpose: str,
) -> dict[str, str]:
    _, instance = await _load_vk_instance(instance_id=instance_id, session=session, container=container)
    client_id = _require_vk_client_id(instance)

    settings = get_settings()
    redirect_uri = f"{settings.app_base_url.rstrip('/')}/auth/vk/callback"
    oauth_session = vk_oauth_store.create(
        adapter_instance_id=instance_id,
        redirect_uri=redirect_uri,
        client_id=client_id,
        scope=scope,
        purpose=purpose,
    )
    code_challenge = build_code_challenge(oauth_session.code_verifier)
    url = build_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=oauth_session.state,
        code_challenge=code_challenge,
        scope=scope,
    )
    logger.info(f"vk oauth start | instance_id={instance_id} purpose={purpose} scope={scope}")
    return {"authorize_url": url, "state": oauth_session.state}


def _build_vk_user_secret_updates(tokens: dict, *, device_id: str) -> dict[str, object]:
    access_token = str(tokens.get("access_token") or "").strip()
    if not access_token:
        raise HTTPException(status_code=400, detail="Не удалось получить пользовательский access token VK.")

    secret_updates: dict[str, object] = {
        "user_access_token_for_media": access_token,
        "vk_oauth_access_token": access_token,
        "vk_oauth_refresh_token": tokens.get("refresh_token"),
        "vk_oauth_id_token": tokens.get("id_token"),
        "vk_oauth_device_id": device_id,
    }
    return secret_updates


@router.get("/api/auth/vk/debug")
async def vk_auth_debug():
    """Diagnostic endpoint to check VK OAuth configuration."""
    settings = get_settings()
    return {
        "app_base_url": settings.app_base_url,
        "redirect_uri": f"{settings.app_base_url.rstrip('/')}/auth/vk/callback",
        "oauth_sessions_count": len(vk_oauth_store._items),
        "note": "Make sure redirect_uri is configured in VK ID cabinet",
    }


@router.post("/api/auth/vk/start")
async def start_vk_auth(payload: dict, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    instance_id = payload.get("instance_id")
    if not instance_id:
        raise HTTPException(status_code=400, detail="instance_id is required")
    return await _start_vk_id_oauth(
        instance_id=instance_id,
        session=session,
        container=container,
        scope=VK_ID_DEFAULT_SCOPE,
        purpose="profile",
    )


@router.post("/api/auth/vk/groups-scope-start")
async def start_vk_groups_scope_auth(payload: dict, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    instance_id = payload.get("instance_id")
    if not instance_id:
        raise HTTPException(status_code=400, detail="instance_id is required")
    return await _start_vk_id_oauth(
        instance_id=instance_id,
        session=session,
        container=container,
        scope=VK_ID_GROUPS_SCOPE,
        purpose="groups",
    )


@router.post("/api/auth/vk/media-start")
async def start_vk_media_auth(payload: dict, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    instance_id = payload.get("instance_id")
    if not instance_id:
        raise HTTPException(status_code=400, detail="instance_id is required")
    return await _start_vk_id_oauth(
        instance_id=instance_id,
        session=session,
        container=container,
        scope=VK_ID_DEFAULT_SCOPE,
        purpose="media",
    )


@router.get("/auth/vk/callback", response_class=HTMLResponse)
async def vk_auth_callback(request: Request, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    qp = {k: v for k, v in request.query_params.items()}
    payload = extract_callback_payload(qp)
    code = payload.get("code")
    state = payload.get("state")
    device_id = payload.get("device_id")
    if not code or not state or not device_id:
        return build_vk_implicit_callback_page()

    oauth_session = vk_oauth_store.pop(str(state))
    if not oauth_session:
        return HTMLResponse("<h3>VK OAuth callback error</h3><p>Сессия авторизации устарела или не найдена.</p>", status_code=400)

    try:
        tokens = await exchange_code_for_token(
            client_id=oauth_session.client_id,
            code=str(code),
            code_verifier=oauth_session.code_verifier,
            device_id=str(device_id),
            redirect_uri=oauth_session.redirect_uri,
            state=str(state),
        )
    except Exception as exc:
        logger.exception(f"vk oauth exchange failed | instance_id={oauth_session.adapter_instance_id}")
        return HTMLResponse(f"<h3>VK OAuth callback error</h3><pre>{escape(str(exc))}</pre>", status_code=500)

    repo = AdapterInstancesRepo(session, SecretBox(container.secrets_encryption_key))
    existing = await repo.get(oauth_session.adapter_instance_id, include_secrets=True)
    if not existing:
        return HTMLResponse("<h3>VK OAuth callback error</h3><p>Инстанс адаптера не найден.</p>", status_code=404)

    config_updates = dict(existing.get("config") or {})
    secret_updates = {}
    if oauth_session.purpose == "groups":
        access_token = str(tokens.get("access_token") or "").strip()
        if not access_token:
            return HTMLResponse("<h3>VK OAuth callback error</h3><p>Не удалось получить token для groups scope.</p>", status_code=400)
        config_updates["vk_groups_oauth_user_id"] = tokens.get("user_id")
        config_updates["vk_groups_oauth_scope"] = oauth_session.scope
        expires_at = compute_expires_at(tokens.get("expires_in"))
        if expires_at is not None:
            config_updates["vk_groups_token_expires_at"] = expires_at
        secret_updates["vk_groups_access_token"] = access_token
    else:
        config_updates["vk_oauth_user_id"] = tokens.get("user_id")
        config_updates["vk_oauth_scope"] = oauth_session.scope
        expires_at = compute_expires_at(tokens.get("expires_in"))
        if expires_at is not None:
            config_updates["vk_oauth_token_expires_at"] = expires_at
        secret_updates = _build_vk_user_secret_updates(tokens, device_id=str(device_id))

    await repo.upsert(
        instance_id=existing["id"],
        adapter_key=existing["adapter_key"],
        platform=existing["platform"],
        display_name=existing["display_name"],
        enabled=existing["enabled"],
        config=config_updates,
        secret_updates=secret_updates,
    )
    logger.info(f"vk oauth success | instance_id={oauth_session.adapter_instance_id} purpose={oauth_session.purpose} user_id={tokens.get('user_id')}")
    message_type = "vk-groups-scope-auth-success" if oauth_session.purpose == "groups" else "vk-auth-success"
    success_title = "VK groups scope подключён" if oauth_session.purpose == "groups" else "VK подключён"
    success_message = (
        "Access token для groups получен. Теперь можно загрузить список админ-групп."
        if oauth_session.purpose == "groups"
        else "User access token VK ID сохранён в настройках этого VK-инстанса."
    )
    return build_vk_auth_success_page(
        title=success_title,
        message=success_message,
        message_type=message_type,
        instance_id=oauth_session.adapter_instance_id,
    )


@router.post("/api/auth/vk/media-finalize")
async def finalize_vk_media_oauth(payload: dict, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    state = str(payload.get("state") or "").strip()
    access_token = str(payload.get("access_token") or "").strip()
    user_id = payload.get("user_id")
    if not state:
        raise HTTPException(status_code=400, detail="state is required")
    if not access_token:
        raise HTTPException(status_code=400, detail="access_token is required")

    oauth_session = vk_oauth_store.pop(state)
    if not oauth_session:
        raise HTTPException(status_code=400, detail="VK media OAuth session not found or expired")

    repo = AdapterInstancesRepo(session, SecretBox(container.secrets_encryption_key))
    existing = await repo.get(oauth_session.adapter_instance_id, include_secrets=True)
    if not existing:
        raise HTTPException(status_code=404, detail="Adapter instance not found")

    config_updates = dict(existing.get("config") or {})
    config_updates["vk_media_oauth_user_id"] = user_id
    config_updates["vk_media_oauth_scope"] = oauth_session.scope

    secret_updates = {
        "user_access_token_for_media": access_token,
        "vk_media_access_token": access_token,
    }

    await repo.upsert(
        instance_id=existing["id"],
        adapter_key=existing["adapter_key"],
        platform=existing["platform"],
        display_name=existing["display_name"],
        enabled=existing["enabled"],
        config=config_updates,
        secret_updates=secret_updates,
    )
    logger.info(f"vk media oauth success | instance_id={oauth_session.adapter_instance_id} user_id={user_id}")
    return {"ok": True, "instance_id": oauth_session.adapter_instance_id}


@router.get("/auth/vk/media-callback", response_class=HTMLResponse)
async def vk_media_oauth_callback(request: Request, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    return build_vk_implicit_callback_page()


@router.post("/api/auth/vk/groups")
async def get_vk_admin_groups(payload: dict, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    """Get list of groups where user is admin, using the VK ID access token."""
    import httpx

    instance_id = payload.get("instance_id")
    if not instance_id:
        raise HTTPException(status_code=400, detail="instance_id is required")

    repo = AdapterInstancesRepo(session, SecretBox(container.secrets_encryption_key))
    instance = await repo.get(instance_id, include_secrets=True)
    if not instance:
        raise HTTPException(status_code=404, detail="Adapter instance not found")

    access_tokens = _vk_admin_group_token_candidates(instance)
    if not access_tokens:
        raise HTTPException(status_code=400, detail="VK OAuth token not found. Please authorize first.")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            last_error: dict | None = None
            for token_idx, access_token in enumerate(access_tokens, start=1):
                for attempt in range(1, 4):
                    resp = await client.post(
                        "https://api.vk.com/method/groups.get",
                        data={
                            "access_token": access_token,
                            "filter": "admin",
                            "extended": "1",
                            "count": 1000,
                            "v": "5.199",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    error = data.get("error")
                    if error:
                        last_error = error
                        if _is_vk_transient_token_check_error(error):
                            if attempt < 3:
                                logger.warning(
                                    f"vk groups.get transient token check error | instance_id={instance_id} token_idx={token_idx} attempt={attempt}"
                                )
                                await asyncio.sleep(0.75 * attempt)
                                continue
                            raise HTTPException(
                                status_code=503,
                                detail="VK временно не смог проверить access token. Повтори ещё раз через несколько секунд.",
                            )
                        logger.error(f"groups.get error | instance_id={instance_id} token_idx={token_idx} error={error}")
                        break

                    response = data.get("response")
                    if isinstance(response, dict):
                        items = response.get("items") or []
                    elif isinstance(response, list):
                        items = response
                    else:
                        items = []

                    groups = []
                    for item in items:
                        if isinstance(item, int):
                            groups.append({"id": item, "name": None, "screen_name": None})
                            continue
                        if not isinstance(item, dict):
                            continue
                        if item.get("id") is None:
                            continue
                        groups.append(
                            {
                                "id": item.get("id"),
                                "name": item.get("name"),
                                "screen_name": item.get("screen_name"),
                            }
                        )
                    groups.sort(key=lambda item: str(item.get("name") or item.get("screen_name") or item.get("id")))
                    return {"groups": groups}

            error_msg = str((last_error or {}).get("error_msg") or "Unknown VK API error")
            raise HTTPException(status_code=400, detail=f"VK API error: {error_msg}")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to get admin groups for instance {instance_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get admin groups: {exc}")


@router.post("/api/auth/vk/groups-auth-start")
async def start_vk_groups_oauth(payload: dict, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    """Start Implicit Flow OAuth to get group access token."""
    instance_id = payload.get("instance_id")
    group_ids = str(payload.get("group_ids") or "").strip()

    if not instance_id:
        raise HTTPException(status_code=400, detail="instance_id is required")
    if not group_ids:
        _, instance = await _load_vk_instance(instance_id=instance_id, session=session, container=container)
        group_id = str((instance.get("config") or {}).get("group_id") or "").strip()
        if not group_id:
            raise HTTPException(status_code=400, detail="group_ids is required")
        group_ids = group_id

    _, instance = await _load_vk_instance(instance_id=instance_id, session=session, container=container)
    client_id = _require_vk_client_id(instance)

    settings = get_settings()
    redirect_uri = f"{settings.app_base_url.rstrip('/')}/auth/vk/callback"
    oauth_session = vk_group_oauth_store.create(
        adapter_instance_id=instance_id,
        redirect_uri=redirect_uri,
        client_id=client_id,
        group_ids=group_ids,
    )

    url = build_vk_oauth_group_authorize_url(
        client_id=client_id,
        group_ids=group_ids,
        redirect_uri=redirect_uri,
        state=oauth_session.state,
    )

    logger.info(f"vk groups oauth start | instance_id={instance_id} group_ids={group_ids}")
    return {"authorize_url": url, "state": oauth_session.state, "instance_id": instance_id, "group_ids": group_ids}


@router.post("/api/auth/vk/groups-finalize")
async def finalize_vk_groups_oauth(payload: dict, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    """Persist group access token returned by VK Implicit Flow."""
    state = str(payload.get("state") or "").strip()
    if not state:
        raise HTTPException(status_code=400, detail="state is required")

    oauth_session = vk_group_oauth_store.pop(state)
    if not oauth_session:
        raise HTTPException(status_code=400, detail="VK groups OAuth session not found or expired")

    tokens = payload.get("tokens")
    if not isinstance(tokens, dict) or not tokens:
        raise HTTPException(status_code=400, detail="tokens are required")

    chosen_token = None
    group_ids = [item.strip() for item in str(oauth_session.group_ids).split(",") if item.strip()]
    for group_id in group_ids:
        token = tokens.get(group_id)
        if token:
            chosen_token = token
            break
    if chosen_token is None:
        chosen_token = next((str(token).strip() for token in tokens.values() if str(token).strip()), None)

    if not chosen_token:
        raise HTTPException(status_code=400, detail="group access token not found in callback payload")

    repo = AdapterInstancesRepo(session, SecretBox(container.secrets_encryption_key))
    existing = await repo.get(oauth_session.adapter_instance_id, include_secrets=True)
    if not existing:
        raise HTTPException(status_code=404, detail="Adapter instance not found")

    preferred_group_id = str((existing.get("config") or {}).get("group_id") or "").strip()
    if preferred_group_id and preferred_group_id in tokens and str(tokens.get(preferred_group_id) or "").strip():
        chosen_token = str(tokens[preferred_group_id]).strip()
    else:
        for group_id in [item.strip() for item in str(oauth_session.group_ids).split(",") if item.strip()]:
            token = tokens.get(group_id)
            if token and str(token).strip():
                chosen_token = str(token).strip()
                break

    config_updates = dict(existing.get("config") or {})
    config_updates["vk_oauth_group_ids"] = oauth_session.group_ids

    secret_updates = {
        "token": chosen_token,
        "vk_group_access_tokens": json.dumps(tokens, ensure_ascii=False, separators=(",", ":")),
    }

    await repo.upsert(
        instance_id=existing["id"],
        adapter_key=existing["adapter_key"],
        platform=existing["platform"],
        display_name=existing["display_name"],
        enabled=existing["enabled"],
        config=config_updates,
        secret_updates=secret_updates,
    )
    logger.info(f"vk groups oauth success | instance_id={oauth_session.adapter_instance_id} group_ids={oauth_session.group_ids}")
    return {"ok": True, "instance_id": oauth_session.adapter_instance_id, "group_ids": oauth_session.group_ids}


@router.get("/auth/vk/groups-callback", response_class=HTMLResponse)
async def vk_groups_oauth_callback(request: Request, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    """Handle Implicit Flow callback - parse access_token from fragment via JavaScript."""
    return build_vk_implicit_callback_page()
