from app.adapters.max.adapter import MaxAdapter
from app.adapters.registry import AdapterRegistry
from app.adapters.telegram.adapter import TelegramAdapter
from app.adapters.vk.adapter import VkAdapter
from app.domain.enums import Platform
from app.repositories.message_links_repo import InMemoryMessageLinksRepo
from app.repositories.platform_accounts_repo import InMemoryPlatformAccountsRepo
from app.repositories.processed_events_repo import InMemoryProcessedEventsRepo
from app.repositories.routes_repo import InMemoryRoutesRepo
from app.repositories.rules_repo import InMemoryRulesRepo
from app.services.dedup_service import DedupService
from app.services.delivery_service import DeliveryService
from app.services.ingress_service import IngressService
from app.services.lineage_service import LineageService
from app.services.policy_service import PolicyService
from app.services.routing_service import RoutingService
from app.services.sync_service import SyncService
from app.services.transform_service import TransformService


class Container:
    def __init__(self) -> None:
        self.routes_repo = InMemoryRoutesRepo()
        self.rules_repo = InMemoryRulesRepo()
        self.processed_events_repo = InMemoryProcessedEventsRepo()
        self.message_links_repo = InMemoryMessageLinksRepo()
        self.platform_accounts_repo = InMemoryPlatformAccountsRepo()

        self.adapter_registry = AdapterRegistry(
            {
                Platform.TELEGRAM: TelegramAdapter(),
                Platform.VK: VkAdapter(),
                Platform.MAX: MaxAdapter(),
            }
        )

        self.dedup_service = DedupService(self.processed_events_repo)
        self.routing_service = RoutingService(self.routes_repo, self.rules_repo)
        self.policy_service = PolicyService()
        self.transform_service = TransformService()
        self.lineage_service = LineageService()
        self.delivery_service = DeliveryService(self.adapter_registry, self.message_links_repo)
        self.sync_service = SyncService(
            dedup_service=self.dedup_service,
            routing_service=self.routing_service,
            policy_service=self.policy_service,
            transform_service=self.transform_service,
            delivery_service=self.delivery_service,
            lineage_service=self.lineage_service,
        )
        self.ingress_service = IngressService(self.adapter_registry, self.sync_service)


container = Container()
