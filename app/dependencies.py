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
from app.repositories.message_links_repo import MessageLinksRepo
from app.repositories.processed_events_repo import ProcessedEventsRepo
from app.repositories.routes_repo import RoutesRepo
from app.repositories.rules_repo import RulesRepo
from app.services.dedup_service import DedupService
from app.services.delivery_service import DeliveryService
from app.services.ingress_service import IngressService
from app.services.lineage_service import LineageService
from app.services.policy_service import PolicyService
from app.services.routing_service import RoutingService
from app.services.sync_service import SyncService
from app.services.transform_service import TransformService


@dataclass(slots=True)
class Container:
    session_factory: async_sessionmaker[AsyncSession]
    adapter_registry: AdapterRegistry

    def create_sync_service(self, session: AsyncSession) -> SyncService:
        routes_repo = RoutesRepo(session)
        rules_repo = RulesRepo(session)
        processed_events_repo = ProcessedEventsRepo(session)
        message_links_repo = MessageLinksRepo(session)

        dedup_service = DedupService(processed_events_repo)
        routing_service = RoutingService(routes_repo, rules_repo)
        policy_service = PolicyService()
        transform_service = TransformService()
        lineage_service = LineageService()
        delivery_service = DeliveryService(self.adapter_registry, message_links_repo)

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


@asynccontextmanager
async def lifespan(app):
    settings = get_settings()
    engine, session_factory = create_session_factory(settings)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.container = Container(
        session_factory=session_factory,
        adapter_registry=AdapterRegistry(
            {
                Platform.TELEGRAM: TelegramAdapter(),
                Platform.VK: VkAdapter(),
                Platform.MAX: MaxAdapter(),
            }
        ),
    )

    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    try:
        yield
    finally:
        await engine.dispose()


async def get_session(request: Request):
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_container(request: Request) -> Container:
    return request.app.state.container
