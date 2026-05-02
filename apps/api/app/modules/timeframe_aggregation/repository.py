from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candles.models import Candle
from app.modules.timeframe_aggregation.models import (
    CandleAggregationRun,
    DerivedCandleLineage,
    MultiTimeframeContext,
)


class TimeframeAggregationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: CandleAggregationRun) -> CandleAggregationRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> CandleAggregationRun | None:
        return await self.session.get(CandleAggregationRun, run_id)

    async def list_runs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        symbol_id: UUID | None = None,
        status: str | None = None,
        base_timeframe: str | None = None,
        target_timeframe: str | None = None,
    ) -> list[CandleAggregationRun]:
        statement: Select[tuple[CandleAggregationRun]] = (
            select(CandleAggregationRun)
            .order_by(CandleAggregationRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(CandleAggregationRun.workspace_id == workspace_id)
        if symbol_id is not None:
            statement = statement.where(CandleAggregationRun.symbol_id == symbol_id)
        if status is not None:
            statement = statement.where(CandleAggregationRun.status == status)
        if base_timeframe is not None:
            statement = statement.where(CandleAggregationRun.base_timeframe == base_timeframe)
        if target_timeframe is not None:
            statement = statement.where(CandleAggregationRun.target_timeframe == target_timeframe)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_lineage(self, lineage: DerivedCandleLineage) -> DerivedCandleLineage:
        self.session.add(lineage)
        await self.session.flush()
        await self.session.refresh(lineage)
        return lineage

    async def get_lineage_by_derived_candle_id(
        self,
        derived_candle_id: UUID,
    ) -> list[DerivedCandleLineage]:
        statement: Select[tuple[DerivedCandleLineage]] = (
            select(DerivedCandleLineage)
            .where(DerivedCandleLineage.derived_candle_id == derived_candle_id)
            .order_by(DerivedCandleLineage.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_final_candles(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        source_id: UUID | None,
    ) -> list[Candle]:
        statement: Select[tuple[Candle]] = (
            select(Candle)
            .where(
                Candle.workspace_id == workspace_id,
                Candle.symbol_id == symbol_id,
                Candle.timeframe == timeframe,
                Candle.timestamp >= start_time,
                Candle.timestamp <= end_time,
                Candle.is_final.is_(True),
            )
            .order_by(Candle.timestamp.asc(), Candle.created_at.desc())
        )
        if source_id is not None:
            statement = statement.where(Candle.source_id == source_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_recent_final_candles(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        end_time: datetime,
        source_id: UUID | None,
        limit: int,
    ) -> list[Candle]:
        statement: Select[tuple[Candle]] = (
            select(Candle)
            .where(
                Candle.workspace_id == workspace_id,
                Candle.symbol_id == symbol_id,
                Candle.timeframe == timeframe,
                Candle.timestamp <= end_time,
                Candle.is_final.is_(True),
            )
            .order_by(Candle.timestamp.desc(), Candle.created_at.desc())
            .limit(limit)
        )
        if source_id is not None:
            statement = statement.where(Candle.source_id == source_id)
        result = await self.session.execute(statement)
        candles = list(result.scalars().all())
        return sorted(self.dedupe_candles_by_timestamp(candles), key=lambda candle: candle.timestamp)

    async def get_context_for_analysis_run(
        self,
        analysis_run_id: UUID,
    ) -> MultiTimeframeContext | None:
        statement: Select[tuple[MultiTimeframeContext]] = (
            select(MultiTimeframeContext)
            .where(MultiTimeframeContext.analysis_run_id == analysis_run_id)
            .order_by(MultiTimeframeContext.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_context_for_signal(self, signal_id: UUID) -> MultiTimeframeContext | None:
        statement: Select[tuple[MultiTimeframeContext]] = (
            select(MultiTimeframeContext)
            .where(MultiTimeframeContext.signal_id == signal_id)
            .order_by(MultiTimeframeContext.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def delete_context_for_analysis_run(self, analysis_run_id: UUID) -> None:
        await self.session.execute(
            delete(MultiTimeframeContext).where(
                MultiTimeframeContext.analysis_run_id == analysis_run_id
            )
        )
        await self.session.flush()

    async def delete_context_for_signal(self, signal_id: UUID) -> None:
        await self.session.execute(
            delete(MultiTimeframeContext).where(MultiTimeframeContext.signal_id == signal_id)
        )
        await self.session.flush()

    async def create_context(self, context: MultiTimeframeContext) -> MultiTimeframeContext:
        self.session.add(context)
        await self.session.flush()
        await self.session.refresh(context)
        return context

    def dedupe_candles_by_timestamp(self, candles: list[Candle]) -> list[Candle]:
        by_timestamp: dict[datetime, Candle] = {}
        for candle in candles:
            by_timestamp.setdefault(candle.timestamp, candle)
        return list(by_timestamp.values())
