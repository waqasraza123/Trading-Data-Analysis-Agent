from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.candle_ingestion_performance.models import (
    CandleIngestionConflict,
    CandleIngestionPerformanceRun,
)
from app.modules.candle_ingestion_performance.repository import (
    CandleIngestionPerformanceRepository,
)
from app.modules.candle_ingestion_performance.schemas import (
    CandleIngestionPerformanceRunListFilters,
)


class CandleIngestionPerformanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = CandleIngestionPerformanceRepository(session)

    async def get_run(self, run_id: UUID) -> CandleIngestionPerformanceRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(
                404,
                "candle_ingestion_performance_run_not_found",
                "Candle ingestion performance run not found",
            )
        return run

    async def list_runs(
        self,
        filters: CandleIngestionPerformanceRunListFilters,
    ) -> list[CandleIngestionPerformanceRun]:
        return await self.repository.list_runs(filters)

    async def list_conflicts(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[CandleIngestionConflict]:
        await self.get_run(run_id)
        return await self.repository.list_conflicts(run_id, limit, offset)
