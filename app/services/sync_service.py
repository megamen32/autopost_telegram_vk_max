from copy import deepcopy

from app.utils.hashing import build_post_hash


class SyncService:
    def __init__(
        self,
        dedup_service,
        routing_service,
        policy_service,
        transform_service,
        delivery_service,
        lineage_service,
        adapter_registry=None,
    ) -> None:
        self.dedup_service = dedup_service
        self.routing_service = routing_service
        self.policy_service = policy_service
        self.transform_service = transform_service
        self.delivery_service = delivery_service
        self.lineage_service = lineage_service
        self.adapter_registry = adapter_registry

    async def handle_post(self, post) -> None:
        source_adapter = None
        if self.adapter_registry is not None:
            try:
                source_adapter = self.adapter_registry.get_by_instance(post.source_adapter_id)
            except Exception:
                source_adapter = None

        if await self.dedup_service.is_processed(
            source_platform=post.source_platform.value,
            source_chat_id=post.source_chat_id,
            source_message_id=post.source_message_id,
        ):
            if source_adapter is not None:
                source_adapter._log_info("diagnostics: duplicate event skipped", source_chat_id=post.source_chat_id, source_message_id=post.source_message_id)
            return

        destinations = await self.routing_service.resolve_destinations(post)
        if source_adapter is not None:
            source_adapter._log_info(
                "diagnostics: route lookup completed",
                source_chat_id=post.source_chat_id,
                matched_routes=[route.id for route, _ in destinations],
                matched_count=len(destinations),
            )
        if not destinations and source_adapter is not None:
            source_adapter._log_warning(
                "diagnostics: no route matched incoming post",
                source_chat_id=post.source_chat_id,
                source_message_id=post.source_message_id,
            )

        for route, rule in destinations:
            if not self.lineage_service.can_deliver(post, route.target_adapter_id):
                if source_adapter is not None:
                    source_adapter._log_warning("diagnostics: delivery skipped by lineage", route_id=route.id, target_adapter_id=route.target_adapter_id)
                continue

            post_copy = deepcopy(post)
            post_copy = self.policy_service.apply_rule(post_copy, rule)
            if post_copy is None:
                if source_adapter is not None:
                    source_adapter._log_warning("diagnostics: route policy filtered post", route_id=route.id)
                continue

            post_copy = self.transform_service.transform_for_target(
                post=post_copy,
                target_platform=route.target_platform,
                rule=rule,
            )
            post_copy = self.lineage_service.extend_trace(post_copy, route.target_adapter_id)
            await self.delivery_service.deliver(route, post_copy)
            if source_adapter is not None:
                source_adapter._log_info(
                    "diagnostics: delivery job enqueued",
                    route_id=route.id,
                    target_adapter_id=route.target_adapter_id,
                    target_chat_id=route.target_chat_id,
                )

        await self.dedup_service.mark_processed(
            source_platform=post.source_platform.value,
            source_chat_id=post.source_chat_id,
            source_message_id=post.source_message_id,
            content_hash=build_post_hash(post),
        )
