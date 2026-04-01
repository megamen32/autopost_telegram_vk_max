from app.domain.enums import Platform
from app.domain.models import MessageTrace, UnifiedPost


class LineageService:
    def can_deliver(self, post: UnifiedPost, target_platform: Platform) -> bool:
        if post.trace is None:
            return True
        return target_platform not in post.trace.path

    def extend_trace(self, post: UnifiedPost, next_platform: Platform) -> UnifiedPost:
        if post.trace is None:
            origin_id = f"{post.source_platform.value}:{post.source_chat_id}:{post.source_message_id}"
            post.trace = MessageTrace(origin_id=origin_id, path=[post.source_platform])

        if next_platform not in post.trace.path:
            post.trace.path.append(next_platform)

        return post
