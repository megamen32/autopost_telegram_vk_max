from app.domain.enums import ContentType, RepostMode
from app.domain.models import UnifiedPost
from app.domain.policies import SyncRule


class PolicyService:
    def apply_rule(self, post: UnifiedPost, rule: SyncRule) -> UnifiedPost | None:
        if post.is_repost:
            if not rule.content_policy.allow_reposts:
                return None
            if rule.repost_mode == RepostMode.IGNORE:
                return None
            if rule.repost_mode == RepostMode.PRESERVE_REFERENCE and post.original_platform:
                link_text = (
                    f"\n\n[repost from {post.original_platform.value}:{post.original_chat_id}:{post.original_message_id}]"
                )
                post.text = (post.text or "") + link_text

        filtered_media = []
        image_count = 0
        for item in post.media:
            if item.type == ContentType.IMAGE and rule.content_policy.allow_images:
                if rule.content_policy.max_images is None or image_count < rule.content_policy.max_images:
                    filtered_media.append(item)
                    image_count += 1
            elif item.type == ContentType.VIDEO and rule.content_policy.allow_video:
                filtered_media.append(item)
            elif item.type == ContentType.AUDIO and rule.content_policy.allow_audio:
                filtered_media.append(item)
            elif item.type == ContentType.DOCUMENT and rule.content_policy.allow_documents:
                filtered_media.append(item)

        text = post.text if rule.content_policy.allow_text else None
        if not text and not filtered_media:
            return None

        post.text = text
        post.media = filtered_media
        return post
