from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncRuleORM(Base):
    __tablename__ = "sync_rules"
    __table_args__ = (UniqueConstraint("source_platform", "target_platform", name="uq_sync_rules_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    target_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_images: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_video: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_documents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_reposts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_images: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_video_size_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_audio_size_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drop_unsupported_media: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    repost_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="ignore")
    copy_text_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RouteORM(Base):
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_chat_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    target_chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProcessedEventORM(Base):
    __tablename__ = "processed_events"
    __table_args__ = (
        UniqueConstraint(
            "source_platform",
            "source_chat_id",
            "source_message_id",
            name="uq_processed_events_source_message",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    source_chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    processed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MessageLinkORM(Base):
    __tablename__ = "message_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    origin_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    origin_chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    target_chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)




class PlatformSettingORM(Base):
    __tablename__ = "platform_settings"

    platform: Mapped[str] = mapped_column(String(32), primary_key=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    secrets_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DeliveryJobORM(Base):
    __tablename__ = "delivery_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    route_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    origin_chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    next_attempt_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    available_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lock_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    locked_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dead_lettered_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
