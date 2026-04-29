from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, build_async_database_url, get_settings


@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine | None:
    settings = get_settings()
    if settings.database_url is None:
        return None
    return create_async_engine(
        build_async_database_url(settings.database_url),
        pool_pre_ping=True,
    )


def get_async_session_factory() -> async_sessionmaker[AsyncSession] | None:
    engine = get_async_engine()
    if engine is None:
        return None
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_database_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is not configured"
        raise RuntimeError(msg)
    async with session_factory() as session:
        yield session


async def check_database_connection(settings: Settings | None = None) -> tuple[bool, str]:
    resolved_settings = settings or get_settings()
    if resolved_settings.database_url is None:
        return False, "DATABASE_URL is not configured"

    engine = create_async_engine(
        build_async_database_url(resolved_settings.database_url),
        pool_pre_ping=True,
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return False, "Database connection failed"
    finally:
        await engine.dispose()

    return True, "Database connection succeeded"
