from enum import Enum


class Platform(str, Enum):
    TELEGRAM = "telegram"
    VK = "vk"
    MAX = "max"


class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    REPOST = "repost"


class RepostMode(str, Enum):
    IGNORE = "ignore"
    FLATTEN = "flatten"
    PRESERVE_REFERENCE = "preserve_reference"
