from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "autopost_sync_beta"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/autopost_sync"
    auto_create_tables: bool = True

    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_string_session: str | None = None
    telegram_bot_token: str | None = None
    telegram_session_name: str = "autopost_sync"
    telegram_receive_updates: bool = True
    telegram_sequential_updates: bool = False
    telegram_check_all_chats: bool = True
    telegram_allowed_source_chat_ids: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
