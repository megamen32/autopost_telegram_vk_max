from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.max.adapter import MaxAdapter
from app.adapters.registry import AdapterRegistry
from app.adapters.telegram.adapter import TelegramAdapter
from app.adapters.vk.adapter import VkAdapter
from app.config import get_settings
from app.db.base import Base
from app.db import models as db_models  # noqa: F401
from app.db.session import create_session_factory
from app.domain.enums import Platform
from app.domain.models import UnifiedPost
from app.repositories.delivery_jobs_repo import DeliveryJobsRepo
from app.repositories.processed_events_repo import ProcessedEventsRepo
from app.repositories.routes_repo import RoutesRepo
from app.repositories.rules_repo import RulesRepo
from app.services.dedup_service import DedupService
from app.services.delivery_service import DeliveryService
from app.services.ingress_service import IngressService
from app.services.lineage_service import LineageService
from app.services.platform_settings_service import load_platform_settings_from_db
from app.services.policy_service import PolicyService
from app.services.queue_service import QueueService
from app.services.routing_service import RoutingService
from app.services.sync_service import SyncService
from app.services.transform_service import TransformService
from app.workers.runner import DeliveryWorkerRunner


@dataclass(slots=True)
class Container:
    session_factory: async_sessionmaker[AsyncSession]
    adapter_registry: AdapterRegistry
    delivery_max_attempts: int
    delivery_worker_batch_size: int
    delivery_retry_base_seconds: int
    delivery_retry_max_seconds: int
    delivery_retry_jitter_seconds: int
    delivery_job_lease_seconds: int
    delivery_job_heartbeat_interval_seconds: float
    secrets_encryption_key: str

    def create_sync_service(self, session: AsyncSession) -> SyncService:
        routes_repo = RoutesRepo(session)
        rules_repo = RulesRepo(session)
        processed_events_repo = ProcessedEventsRepo(session)
        delivery_jobs_repo = DeliveryJobsRepo(session)

        dedup_service = DedupService(processed_events_repo)
        routing_service = RoutingService(routes_repo, rules_repo)
        policy_service = PolicyService()
        transform_service = TransformService()
        lineage_service = LineageService()
        queue_service = QueueService(delivery_jobs_repo, max_attempts=self.delivery_max_attempts)
        delivery_service = DeliveryService(queue_service)

        return SyncService(
            dedup_service=dedup_service,
            routing_service=routing_service,
            policy_service=policy_service,
            transform_service=transform_service,
            delivery_service=delivery_service,
            lineage_service=lineage_service,
        )

    def create_ingress_service(self, session: AsyncSession) -> IngressService:
        return IngressService(self.adapter_registry, self.create_sync_service(session))

    async def handle_adapter_post(self, post: UnifiedPost) -> None:
        async with self.session_factory() as session:
            sync_service = self.create_sync_service(session)
            await sync_service.handle_post(post)
            await session.commit()


@asynccontextmanager
async def lifespan(app):
    settings = get_settings()
    engine, session_factory = create_session_factory(settings)
    app.state.engine = engine
    app.state.session_factory = session_factory

    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    platform_settings = await load_platform_settings_from_db(
        session_factory=session_factory,
        secrets_encryption_key=settings.secrets_encryption_key,
    )
    tg = platform_settings[Platform.TELEGRAM.value]
    vk = platform_settings[Platform.VK.value]
    mx = platform_settings[Platform.MAX.value]

    telegram_adapter = TelegramAdapter(
        api_id=tg["config"].get("api_id"),
        api_hash=tg["secrets"].get("api_hash"),
        string_session=tg["secrets"].get("string_session"),
        bot_token=tg["secrets"].get("bot_token"),
        session_name=tg["config"].get("session_name") or "autopost_sync",
        receive_updates=bool(tg["config"].get("receive_updates", True)),
        sequential_updates=bool(tg["config"].get("sequential_updates", False)),
        allowed_source_chat_ids=tg["config"].get("allowed_source_chat_ids") or [],
    )

    container = Container(
        session_factory=session_factory,
        adapter_registry=AdapterRegistry(
            {
                Platform.TELEGRAM: telegram_adapter,
                Platform.VK: VkAdapter(
                    token=vk["secrets"].get("token"),
                    group_id=vk["config"].get("group_id"),
                    api_version=vk["config"].get("api_version") or "5.199",
                    confirmation_token=vk["secrets"].get("confirmation_token"),
                    secret=vk["secrets"].get("secret"),
                    receive_updates=bool(vk["config"].get("receive_updates", True)),
                    allowed_source_chat_ids=vk["config"].get("allowed_source_chat_ids") or [],
                ),
                Platform.MAX: MaxAdapter(
                    token=mx["secrets"].get("token"),
                    webhook_url=mx["config"].get("webhook_url"),
                    secret=mx["secrets"].get("secret"),
                    receive_updates=bool(mx["config"].get("receive_updates", True)),
                    update_types=mx["config"].get("update_types") or ["message_created"],
                    allowed_source_chat_ids=mx["config"].get("allowed_source_chat_ids") or [],
                ),
            }
        ),
        delivery_max_attempts=settings.delivery_max_attempts,
        delivery_worker_batch_size=settings.delivery_worker_batch_size,
        delivery_retry_base_seconds=settings.delivery_retry_base_seconds,
        delivery_retry_max_seconds=settings.delivery_retry_max_seconds,
        delivery_retry_jitter_seconds=settings.delivery_retry_jitter_seconds,
        delivery_job_lease_seconds=settings.delivery_job_lease_seconds,
        delivery_job_heartbeat_interval_seconds=settings.delivery_job_heartbeat_interval_seconds,
        secrets_encryption_key=settings.secrets_encryption_key,
    )
    app.state.container = container

    await telegram_adapter.startup(on_post=container.handle_adapter_post)
    await container.adapter_registry.get(Platform.MAX).startup(on_post=container.handle_adapter_post)

    worker = None
    if settings.delivery_queue_enabled:
        worker = DeliveryWorkerRunner(container, poll_interval_seconds=settings.delivery_worker_poll_interval_seconds)
        await worker.start()
    app.state.delivery_worker = worker

    try:
        yield
    finally:
        if worker is not None:
            await worker.stop()
        await telegram_adapter.shutdown()
        await container.adapter_registry.get(Platform.MAX).shutdown()
        await engine.dispose()


async def get_session(request: Request):
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_container(request: Request) -> Container:
    return request.app.state.container
