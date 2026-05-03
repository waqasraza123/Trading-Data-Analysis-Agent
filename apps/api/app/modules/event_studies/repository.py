from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, distinct, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candles.models import Candle
from app.modules.event_studies.models import EventStudyResult, EventStudyRun
from app.modules.news.models import NewsEvent
from app.modules.symbols.models import Symbol


class EventStudyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: EventStudyRun) -> EventStudyRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> EventStudyRun | None:
        return await self.session.get(EventStudyRun, run_id)

    async def create_results(self, results: list[EventStudyResult]) -> list[EventStudyResult]:
        self.session.add_all(results)
        await self.session.flush()
        for result in results:
            await self.session.refresh(result)
        return results

    async def list_results(self, run_id: UUID, limit: int, offset: int) -> list[EventStudyResult]:
        statement: Select[tuple[EventStudyResult]] = (
            select(EventStudyResult)
            .where(EventStudyResult.event_study_run_id == run_id)
            .order_by(EventStudyResult.reaction_label, EventStudyResult.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_runs_by_news_event(
        self,
        news_event_id: UUID,
        limit: int,
        offset: int,
    ) -> list[EventStudyRun]:
        statement: Select[tuple[EventStudyRun]] = (
            select(EventStudyRun)
            .where(EventStudyRun.news_event_id == news_event_id)
            .order_by(EventStudyRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_symbols_by_ids(self, symbol_ids: list[UUID]) -> list[Symbol]:
        if not symbol_ids:
            return []
        statement: Select[tuple[Symbol]] = (
            select(Symbol).where(Symbol.id.in_(symbol_ids)).where(Symbol.is_active.is_(True))
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_relevant_symbols(self, event: NewsEvent) -> list[Symbol]:
        statement: Select[tuple[Symbol]] = select(Symbol).where(Symbol.is_active.is_(True))
        if event.symbol_id is not None:
            statement = statement.where(Symbol.id == event.symbol_id)
        else:
            event_asset = normalized_token(event.asset)
            event_currency = normalized_token(event.currency)
            relevance_tokens = {token for token in {event_asset, event_currency} if token is not None}
            if not relevance_tokens:
                return []
            statement = statement.where(
                or_(
                    Symbol.symbol.in_(relevance_tokens),
                    Symbol.base_asset.in_(relevance_tokens),
                    Symbol.quote_asset.in_(relevance_tokens),
                )
            )
        result = await self.session.execute(statement.order_by(Symbol.symbol.asc()))
        return list(result.scalars().all())

    async def list_source_ids_for_window(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[UUID]:
        statement = (
            select(distinct(Candle.source_id))
            .where(Candle.workspace_id == workspace_id)
            .where(Candle.symbol_id == symbol_id)
            .where(Candle.timeframe == timeframe)
            .where(Candle.timestamp >= start_time)
            .where(Candle.timestamp <= end_time)
            .where(Candle.is_final.is_(True))
        )
        result = await self.session.execute(statement)
        return [source_id for source_id in result.scalars().all() if source_id is not None]

    async def list_final_candles(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        source_id: UUID | None,
        include_end: bool,
    ) -> list[Candle]:
        statement: Select[tuple[Candle]] = (
            select(Candle)
            .where(Candle.workspace_id == workspace_id)
            .where(Candle.symbol_id == symbol_id)
            .where(Candle.timeframe == timeframe)
            .where(Candle.timestamp >= start_time)
            .where(Candle.is_final.is_(True))
            .order_by(Candle.timestamp.asc())
        )
        if include_end:
            statement = statement.where(Candle.timestamp <= end_time)
        else:
            statement = statement.where(Candle.timestamp < end_time)
        if source_id is not None:
            statement = statement.where(Candle.source_id == source_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())


def normalized_token(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None
