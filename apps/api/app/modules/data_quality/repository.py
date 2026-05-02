from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candles.models import Candle
from app.modules.data_quality.models import DataQualityFinding, DataQualityRun


class DataQualityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: DataQualityRun, findings: list[DataQualityFinding]) -> DataQualityRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        for finding in findings:
            finding.data_quality_run_id = run.id
            finding.workspace_id = run.workspace_id
        self.session.add_all(findings)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> DataQualityRun | None:
        return await self.session.get(DataQualityRun, run_id)

    async def list_findings(self, run_id: UUID, limit: int, offset: int) -> list[DataQualityFinding]:
        statement: Select[tuple[DataQualityFinding]] = (
            select(DataQualityFinding)
            .where(DataQualityFinding.data_quality_run_id == run_id)
            .order_by(DataQualityFinding.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def summarize_candles(
        self,
        workspace_id: UUID,
        symbol_id: UUID | None = None,
        source_id: UUID | None = None,
        timeframe: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> tuple[int, int, float | None]:
        statement = select(
            func.count(Candle.id),
            func.count(Candle.id).filter(Candle.is_final.is_(False)),
            func.avg(Candle.quality_score),
        ).where(Candle.workspace_id == workspace_id)
        if symbol_id is not None:
            statement = statement.where(Candle.symbol_id == symbol_id)
        if source_id is not None:
            statement = statement.where(Candle.source_id == source_id)
        if timeframe is not None:
            statement = statement.where(Candle.timeframe == timeframe)
        if start_time is not None:
            statement = statement.where(Candle.timestamp >= start_time)
        if end_time is not None:
            statement = statement.where(Candle.timestamp <= end_time)
        row = (await self.session.execute(statement)).one()
        return int(row[0] or 0), int(row[1] or 0), float(row[2]) if row[2] is not None else None
