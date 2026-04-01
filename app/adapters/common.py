from app.domain.enums import ContentType
from app.domain.models import MediaItem


def parse_media_items(payload_media: list[dict] | None) -> list[MediaItem]:
    items: list[MediaItem] = []
    for raw in payload_media or []:
        try:
            content_type = ContentType(raw["type"])
        except Exception:
            continue
        items.append(
            MediaItem(
                type=content_type,
                file_id=raw.get("file_id"),
                url=raw.get("url"),
                mime_type=raw.get("mime_type"),
                filename=raw.get("filename"),
                size_bytes=raw.get("size_bytes"),
                meta=raw.get("meta") or {},
            )
        )
    return items
