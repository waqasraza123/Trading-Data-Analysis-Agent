from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_database_session


async def database_session() -> AsyncIterator[AsyncSession]:
    async for session in get_database_session():
        yield session
