import hashlib
import json


def build_post_hash(post) -> str:
    payload = {
        "source_platform": post.source_platform.value,
        "source_chat_id": post.source_chat_id,
        "source_message_id": post.source_message_id,
        "text": post.text,
        "media": [
            {
                "type": item.type.value,
                "file_id": item.file_id,
                "url": item.url,
                "filename": item.filename,
                "size_bytes": item.size_bytes,
            }
            for item in post.media
        ],
        "is_repost": post.is_repost,
        "original_platform": post.original_platform.value if post.original_platform else None,
        "original_chat_id": post.original_chat_id,
        "original_message_id": post.original_message_id,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
