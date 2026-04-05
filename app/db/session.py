from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings


def create_session_factory(settings: Settings) -> tuple:
    engine_kwargs = {
        "echo": settings.sql_debug,
        "future": True,
        "pool_pre_ping": True,
    }
    if settings.database_url.startswith("sqlite+aiosqlite:///:memory:"):
        engine_kwargs["poolclass"] = StaticPool
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_async_engine(settings.database_url, **engine_kwargs)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory
