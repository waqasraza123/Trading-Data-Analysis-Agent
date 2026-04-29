from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.symbols.models import MarketType, Symbol
from app.modules.symbols.repository import SymbolRepository
from app.modules.symbols.schemas import SymbolCreate, SymbolUpdate


class SymbolService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SymbolRepository(session)

    async def create_symbol(self, payload: SymbolCreate) -> Symbol:
        symbol = Symbol(**payload.model_dump(mode="python"))
        try:
            created_symbol = await self.repository.create(symbol)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(409, "symbol_conflict", "Symbol already exists") from error
        return created_symbol

    async def list_symbols(
        self,
        limit: int,
        offset: int,
        is_active: bool | None = None,
    ) -> list[Symbol]:
        return await self.repository.list(limit=limit, offset=offset, is_active=is_active)

    async def get_symbol(self, symbol_id: UUID) -> Symbol:
        symbol = await self.repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        return symbol

    async def update_symbol(self, symbol_id: UUID, payload: SymbolUpdate) -> Symbol:
        symbol = await self.get_symbol(symbol_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        self.validate_update(symbol, updates)
        for field_name, field_value in updates.items():
            setattr(symbol, field_name, field_value)
        try:
            await self.session.flush()
            await self.session.refresh(symbol)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(409, "symbol_conflict", "Symbol already exists") from error
        return symbol

    def validate_update(self, symbol: Symbol, updates: dict[str, object]) -> None:
        market_type = updates.get("market_type", symbol.market_type)
        pip_size = updates.get("pip_size", symbol.pip_size)
        tick_size = updates.get("tick_size", symbol.tick_size)

        if market_type == MarketType.FOREX and not isinstance(pip_size, Decimal):
            raise AppError(422, "invalid_symbol", "Forex symbols require pip_size")
        if market_type == MarketType.CRYPTO and not isinstance(tick_size, Decimal):
            raise AppError(422, "invalid_symbol", "Crypto symbols require tick_size")
