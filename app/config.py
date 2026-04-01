from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "autopost_sync_alpha"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
