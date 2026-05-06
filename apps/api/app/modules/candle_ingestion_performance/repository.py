from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candle_ingestion_performance.models import (
    CandleIngestionConflict,
    CandleIngestionPerformanceRun,
)
from app.modules.candle_ingestion_performance.schemas import (
    CandleIngestionPerformanceRunListFilters,
)


class CandleIngestionPerformanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_run(self, run_id: UUID) -> CandleIngestionPerformanceRun | None:
        return await self.session.get(CandleIngestionPerformanceRun, run_id)

    async def list_runs(
        self,
        filters: CandleIngestionPerformanceRunListFilters,
    ) -> list[CandleIngestionPerformanceRun]:
        statement: Select[tuple[CandleIngestionPerformanceRun]] = (
            select(CandleIngestionPerformanceRun)
            .where(CandleIngestionPerformanceRun.workspace_id == filters.workspace_id)
            .order_by(CandleIngestionPerformanceRun.created_at.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        if filters.import_batch_id is not None:
            statement = statement.where(
                CandleIngestionPerformanceRun.import_batch_id == filters.import_batch_id
            )
        if filters.provider_polling_request_id is not None:
            statement = statement.where(
                CandleIngestionPerformanceRun.provider_polling_request_id
                == filters.provider_polling_request_id
            )
        if filters.source_id is not None:
            statement = statement.where(
                CandleIngestionPerformanceRun.source_id == filters.source_id
            )
        if filters.symbol_id is not None:
            statement = statement.where(
                CandleIngestionPerformanceRun.symbol_id == filters.symbol_id
            )
        if filters.ingestion_mode is not None:
            statement = statement.where(
                CandleIngestionPerformanceRun.ingestion_mode == filters.ingestion_mode.value
            )
        if filters.status is not None:
            statement = statement.where(
                CandleIngestionPerformanceRun.status == filters.status.value
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_conflicts(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[CandleIngestionConflict]:
        statement: Select[tuple[CandleIngestionConflict]] = (
            select(CandleIngestionConflict)
            .where(CandleIngestionConflict.performance_run_id == run_id)
            .order_by(CandleIngestionConflict.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
