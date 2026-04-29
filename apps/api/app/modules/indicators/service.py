from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisRun
from app.modules.candles.models import Candle
from app.modules.indicators.engine import calculate_indicator_snapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.indicators.repository import IndicatorSnapshotRepository


class IndicatorSnapshotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = IndicatorSnapshotRepository(session)

    async def create_snapshot(
        self,
        analysis_run: AnalysisRun,
        analysis_candles: list[Candle],
        warmup_candles: list[Candle],
        baseline_candles: list[Candle],
    ) -> IndicatorSnapshot:
        indicators = calculate_indicator_snapshot(
            analysis_candles=analysis_candles,
            warmup_candles=warmup_candles,
            baseline_candles=baseline_candles,
        )
        return await self.repository.create(
            IndicatorSnapshot(
                analysis_run_id=analysis_run.id,
                workspace_id=analysis_run.workspace_id,
                symbol_id=analysis_run.symbol_id,
                timeframe=analysis_run.timeframe,
                indicators_json=indicators,
            )
        )

    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> IndicatorSnapshot | None:
        return await self.repository.get_by_analysis_run_id(analysis_run_id)
