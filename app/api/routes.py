from app.utils.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.policies import ContentPolicy, Route
from app.repositories.routes_repo import RoutesRepo
from app.schemas.api import RouteSchema
from app.dependencies import get_session, get_container

logger = get_logger("autopost_sync.routes")

router = APIRouter(prefix="/routes", tags=["routes"])


def _slugify(value: str) -> str:
    value = (value or '').strip().lower()
    out = []
    prev_dash = False
    for ch in value:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        else:
            if not prev_dash:
                out.append('-')
                prev_dash = True
    slug = ''.join(out).strip('-')
    return slug or 'route'


def _build_route_id(data: dict) -> str:
    src = _slugify(str(data.get('source_adapter_id') or 'src'))
    dst = _slugify(str(data.get('target_adapter_id') or 'dst'))
    src_chat = _slugify(str(data.get('source_chat_id') or 'source'))[:32]
    dst_chat = _slugify(str(data.get('target_chat_id') or 'target'))[:32]
    return f"{src}-to-{dst}-{src_chat}-to-{dst_chat}"[:120]


@router.get("")
async def list_routes(session: AsyncSession = Depends(get_session)):
    return await RoutesRepo(session).list_all()


async def _normalize_telegram_route_refs(data: dict, container) -> dict:
    pairs = [
        ("source_platform", "source_adapter_id", "source_chat_id", "source_chat_canonical"),
        ("target_platform", "target_adapter_id", "target_chat_id", "target_chat_canonical"),
    ]
    for platform_key, adapter_key, chat_key, canonical_key in pairs:
        if str(data.get(platform_key)) != "telegram":
            continue
        adapter_id = data.get(adapter_key)
        chat_value = data.get(chat_key)
        if not adapter_id or chat_value in (None, ""):
            continue
        try:
            adapter = container.adapter_registry.get_by_instance(adapter_id)
        except Exception:
            adapter = None
        resolved = None
        if adapter is not None:
            resolver = getattr(adapter, "resolve_chat_reference", None)
            if resolver is not None:
                try:
                    logger.info(f"telegram resolve start | {{'adapter_id': {adapter_id!r}, 'raw': {chat_value!r}}}")
                    resolved = await resolver(chat_value)
                    logger.info(
                        f"telegram resolve success | {{'adapter_id': {adapter_id!r}, 'raw': {chat_value!r}, 'canonical': {resolved!r}}}"
                    )
                except Exception as exc:
                    logger.warning(
                        f"telegram resolve failed | {{'adapter_id': {adapter_id!r}, 'raw': {chat_value!r}, 'reason': {str(exc)!r}}}"
                    )
                    if adapter is not None:
                        try:
                            adapter._log_warning("telegram resolve failed; using fallback canonicalization", raw=chat_value, reason=str(exc))
                        except Exception:
                            pass
                    resolved = None
        if resolved is None:
            from app.utils.chat_refs import canonicalize_telegram_chat_ref
            resolved = canonicalize_telegram_chat_ref(chat_value)
            logger.info(f"telegram resolve fallback canonicalization | {{'raw': {chat_value!r}, 'canonical': {resolved!r}}}")
        data[canonical_key] = str(resolved) if resolved not in (None, "") else None
    return data


@router.post("")
async def create_or_update_route(payload: RouteSchema, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    data = payload.model_dump()
    data = await _normalize_telegram_route_refs(data, container)
    if not data.get("id"):
        data["id"] = _build_route_id(data)
    data["content_policy"] = ContentPolicy(**payload.content_policy.model_dump())
    route = Route(**data)
    logger.info(
        "route upsert | "
        f"{{'route_id': {data.get('id')!r}, 'source_adapter_id': {data.get('source_adapter_id')!r}, 'source_chat_id': {data.get('source_chat_id')!r}, "
        f"'source_chat_canonical': {data.get('source_chat_canonical')!r}, 'target_adapter_id': {data.get('target_adapter_id')!r}, "
        f"'target_chat_id': {data.get('target_chat_id')!r}, 'target_chat_canonical': {data.get('target_chat_canonical')!r}}}"
    )
    return await RoutesRepo(session).upsert(route)


@router.delete("/{route_id}")
async def delete_route(route_id: str, session: AsyncSession = Depends(get_session)):
    deleted = await RoutesRepo(session).delete(route_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Route not found")
    return {"ok": True}
