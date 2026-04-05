from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import ContentType, Platform


@dataclass(slots=True)
class MediaItem:
    type: ContentType
    file_id: str | None = None
    url: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    size_bytes: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MessageTrace:
    origin_id: str
    path: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UnifiedPost:
    source_platform: Platform
    source_adapter_id: str
    source_chat_id: str
    source_message_id: str
    text: str | None = None
    media: list[MediaItem] = field(default_factory=list)
    is_repost: bool = False
    original_platform: Platform | None = None
    original_chat_id: str | None = None
    original_message_id: str | None = None
    trace: MessageTrace | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
