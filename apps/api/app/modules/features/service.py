from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.analysis.models import AnalysisRun
from app.modules.candles.models import Candle
from app.modules.candles.quality import CandleQualityReport
from app.modules.features.engine import calculate_feature_snapshot
from app.modules.features.models import FeatureSnapshot
from app.modules.features.repository import FeatureSnapshotRepository
from app.modules.symbols.repository import SymbolRepository


class FeatureSnapshotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = FeatureSnapshotRepository(session)
        self.symbol_repository = SymbolRepository(session)

    async def create_snapshot(
        self,
        analysis_run: AnalysisRun,
        analysis_candles: list[Candle],
        warmup_candles: list[Candle],
        baseline_candles: list[Candle],
        data_quality: CandleQualityReport,
    ) -> FeatureSnapshot:
        symbol = await self.symbol_repository.get_by_id(analysis_run.symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        features = calculate_feature_snapshot(
            symbol=symbol,
            analysis_candles=analysis_candles,
            warmup_candles=warmup_candles,
            baseline_candles=baseline_candles,
            data_quality=data_quality,
        )
        return await self.repository.create(
            FeatureSnapshot(
                analysis_run_id=analysis_run.id,
                workspace_id=analysis_run.workspace_id,
                symbol_id=analysis_run.symbol_id,
                timeframe=analysis_run.timeframe,
                start_time=analysis_run.start_time,
                end_time=analysis_run.end_time,
                features_json=features,
            )
        )

    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> FeatureSnapshot | None:
        return await self.repository.get_by_analysis_run_id(analysis_run_id)
