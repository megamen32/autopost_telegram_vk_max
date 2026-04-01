from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "autopost_sync_beta"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    app_base_url: str = "http://127.0.0.1:8000"
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/autopost_sync"
    auto_create_tables: bool = True
    secrets_encryption_key: str = "dev-not-secure-change-me"

    delivery_queue_enabled: bool = True
    delivery_worker_poll_interval_seconds: float = 1.0
    delivery_worker_batch_size: int = 10
    delivery_job_lease_seconds: int = 300
    delivery_job_heartbeat_interval_seconds: float = 30.0
    delivery_max_attempts: int = 8
    delivery_retry_base_seconds: int = 5
    delivery_retry_max_seconds: int = 900
    delivery_retry_jitter_seconds: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
