from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candles.models import Candle
from app.modules.cross_asset_context.models import (
    CrossAssetContextResult,
    CrossAssetContextRun,
)
from app.modules.symbols.models import Symbol


class CrossAssetContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: CrossAssetContextRun) -> CrossAssetContextRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def create_results(
        self,
        results: list[CrossAssetContextResult],
    ) -> list[CrossAssetContextResult]:
        if not results:
            return []
        self.session.add_all(results)
        await self.session.flush()
        for result in results:
            await self.session.refresh(result)
        return results

    async def get_run(self, run_id: UUID) -> CrossAssetContextRun | None:
        return await self.session.get(CrossAssetContextRun, run_id)

    async def get_latest_for_analysis_run(
        self,
        analysis_run_id: UUID,
        context_version: str,
    ) -> CrossAssetContextRun | None:
        statement: Select[tuple[CrossAssetContextRun]] = (
            select(CrossAssetContextRun)
            .where(
                CrossAssetContextRun.analysis_run_id == analysis_run_id,
                CrossAssetContextRun.context_version == context_version,
            )
            .order_by(CrossAssetContextRun.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_for_signal(
        self,
        signal_id: UUID,
        context_version: str,
    ) -> CrossAssetContextRun | None:
        statement: Select[tuple[CrossAssetContextRun]] = (
            select(CrossAssetContextRun)
            .where(
                CrossAssetContextRun.signal_id == signal_id,
                CrossAssetContextRun.context_version == context_version,
            )
            .order_by(CrossAssetContextRun.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def delete_for_analysis_run(self, analysis_run_id: UUID, context_version: str) -> None:
        await self.session.execute(
            delete(CrossAssetContextRun).where(
                CrossAssetContextRun.analysis_run_id == analysis_run_id,
                CrossAssetContextRun.context_version == context_version,
            )
        )
        await self.session.flush()

    async def delete_for_signal(self, signal_id: UUID, context_version: str) -> None:
        await self.session.execute(
            delete(CrossAssetContextRun).where(
                CrossAssetContextRun.signal_id == signal_id,
                CrossAssetContextRun.context_version == context_version,
            )
        )
        await self.session.flush()

    async def list_results(
        self,
        context_run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[CrossAssetContextResult]:
        statement: Select[tuple[CrossAssetContextResult]] = (
            select(CrossAssetContextResult)
            .where(CrossAssetContextResult.context_run_id == context_run_id)
            .order_by(CrossAssetContextResult.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_symbols_by_ids(self, symbol_ids: list[UUID]) -> list[Symbol]:
        if not symbol_ids:
            return []
        statement: Select[tuple[Symbol]] = select(Symbol).where(Symbol.id.in_(symbol_ids))
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
        return dedupe_candles_by_timestamp(list(result.scalars().all()))


def dedupe_candles_by_timestamp(candles: list[Candle]) -> list[Candle]:
    by_timestamp: dict[datetime, Candle] = {}
    for candle in candles:
        by_timestamp.setdefault(candle.timestamp, candle)
    return list(by_timestamp.values())
