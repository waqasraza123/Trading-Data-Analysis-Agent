from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.market_sessions.models import MarketSessionContext


class MarketSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, context: MarketSessionContext) -> MarketSessionContext:
        self.session.add(context)
        await self.session.flush()
        await self.session.refresh(context)
        return context

    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> MarketSessionContext | None:
        statement: Select[tuple[MarketSessionContext]] = (
            select(MarketSessionContext)
            .where(MarketSessionContext.analysis_run_id == analysis_run_id)
            .order_by(MarketSessionContext.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_signal_id(self, signal_id: UUID) -> MarketSessionContext | None:
        statement: Select[tuple[MarketSessionContext]] = (
            select(MarketSessionContext)
            .where(MarketSessionContext.signal_id == signal_id)
            .order_by(MarketSessionContext.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
