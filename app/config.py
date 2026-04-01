from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "autopost_sync_beta"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/autopost_sync"
    auto_create_tables: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
