from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.definitions import AdapterDefinitionRegistry
from app.dependencies import get_container, get_session
from app.repositories.adapter_instances_repo import AdapterInstancesRepo
from app.utils.crypto import SecretBox
from app.schemas.api import AdapterInstanceUpsertSchema

router = APIRouter(tags=["adapter_instances"])


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
    return await repo.upsert(
        instance_id=payload.id,
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
    ok = await repo.delete(instance_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Adapter instance not found')
    return {'ok': True}
