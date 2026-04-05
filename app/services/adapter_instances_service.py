from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.adapters.definitions import AdapterDefinitionRegistry
from app.adapters.registry import AdapterRegistry
from app.repositories.adapter_instances_repo import AdapterInstancesRepo
from app.utils.crypto import SecretBox
from app.services.adapter_runtime import AdapterRuntimeMonitor


async def load_adapter_registry_from_db(session_factory: async_sessionmaker, *, secrets_encryption_key: str, runtime_monitor: AdapterRuntimeMonitor | None = None) -> tuple[AdapterRegistry, list[dict]]:
    defs = AdapterDefinitionRegistry()
    async with session_factory() as session:
        repo = AdapterInstancesRepo(session, SecretBox(secrets_encryption_key))
        rows = await repo.list_all(include_secrets=True)
    adapters: dict[str, object] = {}
    for row in rows:
        if not row.get('enabled', True):
            continue
        adapter = defs.create_adapter(row['adapter_key'], row['id'], row.get('config') or {}, row.get('secrets') or {})
        if runtime_monitor is not None:
            adapter.attach_runtime_monitor(runtime_monitor)
        adapters[row['id']] = adapter
    return AdapterRegistry(adapters), rows
