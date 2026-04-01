from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings


def create_session_factory(settings: Settings) -> tuple:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        future=True,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory
