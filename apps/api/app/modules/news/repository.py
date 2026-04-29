from __future__ import annotations

import builtins
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.news.models import NewsEvent, SignalNewsCorrelation


class NewsEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, event: NewsEvent) -> NewsEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get_by_id(self, news_event_id: UUID) -> NewsEvent | None:
        return await self.session.get(NewsEvent, news_event_id)

    async def list_events(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        currency: str | None = None,
        asset: str | None = None,
        symbol_id: UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> builtins.list[NewsEvent]:
        statement: Select[tuple[NewsEvent]] = (
            select(NewsEvent).order_by(NewsEvent.event_time.desc()).limit(limit).offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(
                or_(NewsEvent.workspace_id == workspace_id, NewsEvent.workspace_id.is_(None))
            )
        if currency is not None:
            statement = statement.where(NewsEvent.currency == currency)
        if asset is not None:
            statement = statement.where(NewsEvent.asset == asset)
        if symbol_id is not None:
            statement = statement.where(NewsEvent.symbol_id == symbol_id)
        if start_time is not None:
            statement = statement.where(NewsEvent.event_time >= start_time)
        if end_time is not None:
            statement = statement.where(NewsEvent.event_time <= end_time)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def find_candidates(
        self,
        workspace_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> builtins.list[NewsEvent]:
        statement: Select[tuple[NewsEvent]] = (
            select(NewsEvent)
            .where(NewsEvent.event_time >= start_time)
            .where(NewsEvent.event_time <= end_time)
            .where(or_(NewsEvent.workspace_id == workspace_id, NewsEvent.workspace_id.is_(None)))
            .order_by(NewsEvent.event_time.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())


class NewsCorrelationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def delete_for_signal(self, signal_id: UUID) -> None:
        await self.session.execute(
            delete(SignalNewsCorrelation).where(SignalNewsCorrelation.signal_id == signal_id)
        )
        await self.session.flush()

    async def create_many(
        self,
        correlations: builtins.list[SignalNewsCorrelation],
    ) -> builtins.list[SignalNewsCorrelation]:
        self.session.add_all(correlations)
        await self.session.flush()
        for correlation in correlations:
            await self.session.refresh(correlation)
        return correlations

    async def list_by_signal_id(self, signal_id: UUID) -> builtins.list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.signal_id == signal_id)
            .order_by(SignalNewsCorrelation.correlation_score.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> builtins.list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.analysis_run_id == analysis_run_id)
            .order_by(SignalNewsCorrelation.correlation_score.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
