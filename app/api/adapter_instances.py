from fastapi import APIRouter, Depends, HTTPException
import re
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.definitions import AdapterDefinitionRegistry
from app.dependencies import get_container, get_session
from app.repositories.adapter_instances_repo import AdapterInstancesRepo
from app.utils.crypto import SecretBox
from app.schemas.api import AdapterInstanceUpsertSchema
from app.utils.logging import get_logger

logger = get_logger("autopost_sync.app")

router = APIRouter(tags=["adapter_instances"])


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9а-яё]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "instance"


async def _generate_unique_instance_id(repo: AdapterInstancesRepo, adapter_key: str, display_name: str) -> str:
    base = f"{_slug(adapter_key)}-{_slug(display_name)}"
    if await repo.get(base) is None:
        return base
    idx = 2
    while await repo.get(f"{base}-{idx}") is not None:
        idx += 1
    return f"{base}-{idx}"


@router.get('/api/adapter-definitions')
async def list_adapter_definitions(container=Depends(get_container)):
    return [item.to_dict() for item in container.definition_registry.list_definitions()]


@router.get('/api/adapter-instances')
async def list_adapter_instances(session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    repo = AdapterInstancesRepo(session, SecretBox(container.secrets_encryption_key))
    return await repo.list_all(include_secrets=False)


@router.post('/api/adapter-instances')
async def create_or_update_adapter_instance(payload: AdapterInstanceUpsertSchema, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    defs = container.definition_registry
    try:
        definition = defs.get(payload.adapter_key)
    except KeyError:
        raise HTTPException(status_code=400, detail='Unknown adapter_key')
    repo = AdapterInstancesRepo(session, SecretBox(container.secrets_encryption_key))
    instance_id = payload.id or await _generate_unique_instance_id(repo, payload.adapter_key, payload.display_name)
    logger.info(f"adapter instance upsert | adapter_key={payload.adapter_key} display_name={payload.display_name} instance_id={instance_id}")
    return await repo.upsert(
        instance_id=instance_id,
        adapter_key=payload.adapter_key,
        platform=definition.platform,
        display_name=payload.display_name,
        enabled=payload.enabled,
        config=payload.config,
        secret_updates=payload.secrets,
    )


@router.delete('/api/adapter-instances/{instance_id}')
async def delete_adapter_instance(instance_id: str, session: AsyncSession = Depends(get_session), container=Depends(get_container)):
    repo = AdapterInstancesRepo(session, SecretBox(container.secrets_encryption_key))
    logger.info(f"adapter instance delete | instance_id={instance_id}")
    ok = await repo.delete(instance_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Adapter instance not found')
    return {'ok': True}
