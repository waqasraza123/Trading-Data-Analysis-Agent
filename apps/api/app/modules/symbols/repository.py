from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.symbols.models import Symbol


class SymbolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, symbol: Symbol) -> Symbol:
        self.session.add(symbol)
        await self.session.flush()
        await self.session.refresh(symbol)
        return symbol

    async def get_by_id(self, symbol_id: UUID) -> Symbol | None:
        return await self.session.get(Symbol, symbol_id)

    async def get_by_symbol(self, symbol_code: str) -> Symbol | None:
        result = await self.session.execute(select(Symbol).where(Symbol.symbol == symbol_code))
        return result.scalar_one_or_none()

    async def list(self, limit: int, offset: int, is_active: bool | None = None) -> list[Symbol]:
        statement: Select[tuple[Symbol]] = (
            select(Symbol).order_by(Symbol.symbol).limit(limit).offset(offset)
        )
        if is_active is not None:
            statement = statement.where(Symbol.is_active == is_active)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count(self, is_active: bool | None = None) -> int:
        statement = select(func.count()).select_from(Symbol)
        if is_active is not None:
            statement = statement.where(Symbol.is_active == is_active)
        result = await self.session.execute(statement)
        return int(result.scalar_one())
