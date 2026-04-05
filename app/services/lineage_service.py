from app.domain.models import UnifiedPost


class LineageService:
    def can_deliver(self, post: UnifiedPost, target_adapter_id: str) -> bool:
        if post.trace is None:
            return True
        return target_adapter_id not in post.trace.path

    def extend_trace(self, post: UnifiedPost, next_adapter_id: str) -> UnifiedPost:
        if post.trace is None:
            post.trace = self._create_trace(post)
        if next_adapter_id not in post.trace.path:
            post.trace.path.append(next_adapter_id)
        return post

    def _create_trace(self, post: UnifiedPost):
        from app.domain.models import MessageTrace

        origin_id = f"{post.source_adapter_id}:{post.source_chat_id}:{post.source_message_id}"
        return MessageTrace(origin_id=origin_id, path=[post.source_adapter_id])
