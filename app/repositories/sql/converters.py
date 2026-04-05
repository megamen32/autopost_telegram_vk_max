from app.db.models import RouteORM, SyncRuleORM
from app.domain.enums import Platform, RepostMode
from app.domain.policies import ContentPolicy, Route, SyncRule


def orm_to_route(row: RouteORM) -> Route:
    return Route(
        id=row.id,
        source_adapter_id=row.source_adapter_id,
        source_platform=Platform(row.source_platform),
        source_chat_id=row.source_chat_id,
        target_adapter_id=row.target_adapter_id,
        target_platform=Platform(row.target_platform),
        target_chat_id=row.target_chat_id,
        enabled=row.enabled,
        has_policy=getattr(row, "has_policy", False),
        policy_enabled=getattr(row, "policy_enabled", True),
        content_policy=ContentPolicy(
            allow_text=getattr(row, "allow_text", True),
            allow_images=getattr(row, "allow_images", True),
            allow_video=getattr(row, "allow_video", True),
            allow_audio=getattr(row, "allow_audio", True),
            allow_documents=getattr(row, "allow_documents", False),
            allow_reposts=getattr(row, "allow_reposts", False),
            max_images=getattr(row, "max_images", None),
            max_video_size_mb=getattr(row, "max_video_size_mb", None),
            max_audio_size_mb=getattr(row, "max_audio_size_mb", None),
            drop_unsupported_media=getattr(row, "drop_unsupported_media", True),
        ),
        repost_mode=RepostMode(getattr(row, "repost_mode", "ignore")),
        copy_text_template=getattr(row, "copy_text_template", None),
    )


def route_to_orm(route: Route) -> RouteORM:
    return RouteORM(
        id=route.id,
        source_adapter_id=route.source_adapter_id,
        source_platform=route.source_platform.value,
        source_chat_id=route.source_chat_id,
        target_adapter_id=route.target_adapter_id,
        target_platform=route.target_platform.value,
        target_chat_id=route.target_chat_id,
        enabled=route.enabled,
        has_policy=route.has_policy,
        policy_enabled=route.policy_enabled,
        allow_text=route.content_policy.allow_text,
        allow_images=route.content_policy.allow_images,
        allow_video=route.content_policy.allow_video,
        allow_audio=route.content_policy.allow_audio,
        allow_documents=route.content_policy.allow_documents,
        allow_reposts=route.content_policy.allow_reposts,
        max_images=route.content_policy.max_images,
        max_video_size_mb=route.content_policy.max_video_size_mb,
        max_audio_size_mb=route.content_policy.max_audio_size_mb,
        drop_unsupported_media=route.content_policy.drop_unsupported_media,
        repost_mode=route.repost_mode.value,
        copy_text_template=route.copy_text_template,
    )


def orm_to_rule(row: SyncRuleORM) -> SyncRule:
    return SyncRule(
        source_platform=Platform(row.source_platform),
        target_platform=Platform(row.target_platform),
        enabled=row.enabled,
        content_policy=ContentPolicy(
            allow_text=row.allow_text,
            allow_images=row.allow_images,
            allow_video=row.allow_video,
            allow_audio=row.allow_audio,
            allow_documents=row.allow_documents,
            allow_reposts=row.allow_reposts,
            max_images=row.max_images,
            max_video_size_mb=row.max_video_size_mb,
            max_audio_size_mb=row.max_audio_size_mb,
            drop_unsupported_media=row.drop_unsupported_media,
        ),
        repost_mode=RepostMode(row.repost_mode),
        copy_text_template=row.copy_text_template,
    )


def update_rule_orm(row: SyncRuleORM, rule: SyncRule) -> SyncRuleORM:
    row.enabled = rule.enabled
    row.allow_text = rule.content_policy.allow_text
    row.allow_images = rule.content_policy.allow_images
    row.allow_video = rule.content_policy.allow_video
    row.allow_audio = rule.content_policy.allow_audio
    row.allow_documents = rule.content_policy.allow_documents
    row.allow_reposts = rule.content_policy.allow_reposts
    row.max_images = rule.content_policy.max_images
    row.max_video_size_mb = rule.content_policy.max_video_size_mb
    row.max_audio_size_mb = rule.content_policy.max_audio_size_mb
    row.drop_unsupported_media = rule.content_policy.drop_unsupported_media
    row.repost_mode = rule.repost_mode.value
    row.copy_text_template = rule.copy_text_template
    return row


def rule_to_orm(rule: SyncRule) -> SyncRuleORM:
    return SyncRuleORM(
        source_platform=rule.source_platform.value,
        target_platform=rule.target_platform.value,
        enabled=rule.enabled,
        allow_text=rule.content_policy.allow_text,
        allow_images=rule.content_policy.allow_images,
        allow_video=rule.content_policy.allow_video,
        allow_audio=rule.content_policy.allow_audio,
        allow_documents=rule.content_policy.allow_documents,
        allow_reposts=rule.content_policy.allow_reposts,
        max_images=rule.content_policy.max_images,
        max_video_size_mb=rule.content_policy.max_video_size_mb,
        max_audio_size_mb=rule.content_policy.max_audio_size_mb,
        drop_unsupported_media=rule.content_policy.drop_unsupported_media,
        repost_mode=rule.repost_mode.value,
        copy_text_template=rule.copy_text_template,
    )
