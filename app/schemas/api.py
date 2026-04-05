from pydantic import BaseModel, Field

from app.domain.enums import Platform, RepostMode


class ContentPolicySchema(BaseModel):
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


class SyncRuleSchema(BaseModel):
    source_platform: Platform
    target_platform: Platform
    enabled: bool
    content_policy: ContentPolicySchema
    repost_mode: RepostMode = RepostMode.IGNORE
    copy_text_template: str | None = None


class RouteSchema(BaseModel):
    id: str = Field(min_length=1)
    source_adapter_id: str = Field(min_length=1)
    source_platform: Platform
    source_chat_id: str
    target_adapter_id: str = Field(min_length=1)
    target_platform: Platform
    target_chat_id: str
    enabled: bool = True

    has_policy: bool = False
    policy_enabled: bool = True
    content_policy: ContentPolicySchema = Field(default_factory=ContentPolicySchema)
    repost_mode: RepostMode = RepostMode.IGNORE
    copy_text_template: str | None = None


class AdapterInstanceUpsertSchema(BaseModel):
    id: str = Field(min_length=1)
    adapter_key: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    enabled: bool = True
    config: dict = Field(default_factory=dict)
    secrets: dict = Field(default_factory=dict)
