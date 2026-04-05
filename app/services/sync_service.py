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
    ) -> None:
        self.dedup_service = dedup_service
        self.routing_service = routing_service
        self.policy_service = policy_service
        self.transform_service = transform_service
        self.delivery_service = delivery_service
        self.lineage_service = lineage_service

    async def handle_post(self, post) -> None:
        if await self.dedup_service.is_processed(
            source_platform=post.source_platform.value,
            source_chat_id=post.source_chat_id,
            source_message_id=post.source_message_id,
        ):
            return

        destinations = await self.routing_service.resolve_destinations(post)
        for route, rule in destinations:
            if not self.lineage_service.can_deliver(post, route.target_adapter_id):
                continue

            post_copy = deepcopy(post)
            post_copy = self.policy_service.apply_rule(post_copy, rule)
            if post_copy is None:
                continue

            post_copy = self.transform_service.transform_for_target(
                post=post_copy,
                target_platform=route.target_platform,
                rule=rule,
            )
            post_copy = self.lineage_service.extend_trace(post_copy, route.target_adapter_id)
            await self.delivery_service.deliver(route, post_copy)

        await self.dedup_service.mark_processed(
            source_platform=post.source_platform.value,
            source_chat_id=post.source_chat_id,
            source_message_id=post.source_message_id,
            content_hash=build_post_hash(post),
        )
