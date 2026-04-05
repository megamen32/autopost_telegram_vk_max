from dataclasses import dataclass, field

from app.domain.enums import Platform, RepostMode


@dataclass(slots=True)
class ContentPolicy:
    allow_text: bool = True
    allow_images: bool = True
    allow_video: bool = True
    allow_audio: bool = True
    allow_documents: bool = False
    allow_reposts: bool = False
    max_images: int | None = None
    max_video_size_mb: int | None = None
    max_audio_size_mb: int | None = None
    drop_unsupported_media: bool = True


@dataclass(slots=True)
class SyncRule:
    source_platform: Platform
    target_platform: Platform
    enabled: bool
    content_policy: ContentPolicy
    repost_mode: RepostMode = RepostMode.IGNORE
    copy_text_template: str | None = None


@dataclass(slots=True)
class Route:
    id: str
    source_adapter_id: str
    source_platform: Platform
    source_chat_id: str
    target_adapter_id: str
    target_platform: Platform
    target_chat_id: str
    enabled: bool = True

    has_policy: bool = False
    policy_enabled: bool = True
    content_policy: ContentPolicy = field(default_factory=ContentPolicy)
    repost_mode: RepostMode = RepostMode.IGNORE
    copy_text_template: str | None = None

    def to_sync_rule(self) -> SyncRule | None:
        if not self.has_policy:
            return None
        return SyncRule(
            source_platform=self.source_platform,
            target_platform=self.target_platform,
            enabled=self.policy_enabled,
            content_policy=self.content_policy,
            repost_mode=self.repost_mode,
            copy_text_template=self.copy_text_template,
        )
