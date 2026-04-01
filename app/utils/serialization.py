from __future__ import annotations

from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, MessageTrace, UnifiedPost
from app.domain.policies import Route


def media_item_to_dict(item: MediaItem) -> dict:
    return {
        "type": item.type.value,
        "file_id": item.file_id,
        "url": item.url,
        "mime_type": item.mime_type,
        "filename": item.filename,
        "size_bytes": item.size_bytes,
        "meta": item.meta,
    }


def media_item_from_dict(data: dict) -> MediaItem:
    return MediaItem(
        type=ContentType(data["type"]),
        file_id=data.get("file_id"),
        url=data.get("url"),
        mime_type=data.get("mime_type"),
        filename=data.get("filename"),
        size_bytes=data.get("size_bytes"),
        meta=data.get("meta") or {},
    )


def unified_post_to_dict(post: UnifiedPost) -> dict:
    return {
        "source_platform": post.source_platform.value,
        "source_chat_id": post.source_chat_id,
        "source_message_id": post.source_message_id,
        "text": post.text,
        "media": [media_item_to_dict(item) for item in post.media],
        "is_repost": post.is_repost,
        "original_platform": post.original_platform.value if post.original_platform else None,
        "original_chat_id": post.original_chat_id,
        "original_message_id": post.original_message_id,
        "trace": {
            "origin_id": post.trace.origin_id,
            "path": [platform.value for platform in post.trace.path],
        } if post.trace else None,
        "raw_payload": post.raw_payload,
    }


def unified_post_from_dict(data: dict) -> UnifiedPost:
    trace_data = data.get("trace")
    trace = None
    if trace_data:
        trace = MessageTrace(
            origin_id=trace_data["origin_id"],
            path=[Platform(item) for item in trace_data.get("path") or []],
        )
    return UnifiedPost(
        source_platform=Platform(data["source_platform"]),
        source_chat_id=data["source_chat_id"],
        source_message_id=data["source_message_id"],
        text=data.get("text"),
        media=[media_item_from_dict(item) for item in data.get("media") or []],
        is_repost=bool(data.get("is_repost", False)),
        original_platform=Platform(data["original_platform"]) if data.get("original_platform") else None,
        original_chat_id=data.get("original_chat_id"),
        original_message_id=data.get("original_message_id"),
        trace=trace,
        raw_payload=data.get("raw_payload") or {},
    )


def route_to_dict(route: Route) -> dict:
    return {
        "id": route.id,
        "source_platform": route.source_platform.value,
        "source_chat_id": route.source_chat_id,
        "target_platform": route.target_platform.value,
        "target_chat_id": route.target_chat_id,
        "enabled": route.enabled,
    }


def route_from_dict(data: dict) -> Route:
    return Route(
        id=data["id"],
        source_platform=Platform(data["source_platform"]),
        source_chat_id=data["source_chat_id"],
        target_platform=Platform(data["target_platform"]),
        target_chat_id=data["target_chat_id"],
        enabled=bool(data.get("enabled", True)),
    )
