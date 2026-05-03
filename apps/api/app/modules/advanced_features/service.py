from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.advanced_features.calculator import (
    AdvancedFeatureCalculationInput,
    AdvancedFeatureCalculator,
    AdvancedFeatureCalculatorSettings,
    safe_json,
)
from app.modules.advanced_features.models import AdvancedFeatureSnapshot
from app.modules.advanced_features.repository import AdvancedFeatureSnapshotRepository
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.analysis.repository import AnalysisRepository
from app.modules.candles.service import CandleService
from app.modules.candles.timeframes import Timeframe
from app.modules.features.service import FeatureSnapshotService
from app.modules.indicators.service import IndicatorSnapshotService
from app.modules.signals.repository import SignalRepository
from app.modules.symbols.repository import SymbolRepository


class AdvancedFeatureSnapshotService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = AdvancedFeatureSnapshotRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.signal_repository = SignalRepository(session)
        self.candle_service = CandleService(session)
        self.feature_snapshot_service = FeatureSnapshotService(session)
        self.indicator_snapshot_service = IndicatorSnapshotService(session)
        self.symbol_repository = SymbolRepository(session)
        self.calculator = AdvancedFeatureCalculator()

    async def generate_for_analysis_run(
        self,
        analysis_run_id: UUID,
        force_recompute: bool = False,
    ) -> AdvancedFeatureSnapshot:
        run = await self.get_analysis_run(analysis_run_id)
        existing = await self.repository.get_by_analysis_run_id(
            analysis_run_id=run.id,
            feature_pack_version=self.feature_pack_version,
        )
        if existing is not None and not force_recompute:
            return existing
        symbol = await self.symbol_repository.get_by_id(run.symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        candles = await self.candle_service.fetch_candle_window(
            workspace_id=run.workspace_id,
            symbol_id=run.symbol_id,
            timeframe=Timeframe(run.timeframe),
            start_time=run.start_time,
            end_time=run.end_time,
            source_id=run.source_id,
            include_partial=False,
        )
        if not candles:
            raise AppError(
                422,
                "advanced_features_no_final_candles",
                "Advanced features require final candles in the analysis window",
            )
        feature_snapshot = await self.feature_snapshot_service.get_by_analysis_run_id(run.id)
        indicator_snapshot = await self.indicator_snapshot_service.get_by_analysis_run_id(run.id)
        calculation = self.calculator.calculate(
            AdvancedFeatureCalculationInput(
                candles=candles,
                symbol=symbol,
                feature_snapshot=feature_snapshot,
                indicator_snapshot=indicator_snapshot,
                settings=self.calculator_settings,
                feature_pack_version=self.feature_pack_version,
            )
        )
        snapshot = AdvancedFeatureSnapshot(
            workspace_id=run.workspace_id,
            analysis_run_id=run.id,
            symbol_id=run.symbol_id,
            timeframe=run.timeframe,
            feature_pack_version=self.feature_pack_version,
            impulse_json=safe_json(calculation.impulse_json),
            correction_json=safe_json(calculation.correction_json),
            wick_pressure_json=safe_json(calculation.wick_pressure_json),
            movement_efficiency_json=safe_json(calculation.movement_efficiency_json),
            compression_expansion_json=safe_json(calculation.compression_expansion_json),
            swing_structure_json=safe_json(calculation.swing_structure_json),
            support_resistance_json=safe_json(calculation.support_resistance_json),
            exhaustion_json=safe_json(calculation.exhaustion_json),
            liquidity_sweep_json=safe_json(calculation.liquidity_sweep_json),
            warnings_json=safe_json(calculation.warnings_json),
            summary=calculation.summary,
        )
        try:
            persisted = await self.repository.upsert(snapshot, existing)
            await self.add_audit_log(
                run,
                "advanced_features_calculated",
                "Advanced price action feature snapshot calculated",
                {
                    "advancedFeatureSnapshotId": str(persisted.id),
                    "featurePackVersion": persisted.feature_pack_version,
                    "forceRecompute": force_recompute,
                },
            )
            await self.session.commit()
            return persisted
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "advanced_feature_snapshot_conflict",
                "Advanced feature snapshot could not be persisted",
            ) from error
        except Exception:
            await self.session.rollback()
            raise

    async def get_for_analysis_run(self, analysis_run_id: UUID) -> AdvancedFeatureSnapshot:
        await self.get_analysis_run(analysis_run_id)
        snapshot = await self.repository.get_by_analysis_run_id(
            analysis_run_id=analysis_run_id,
            feature_pack_version=self.feature_pack_version,
        )
        if snapshot is None:
            raise AppError(
                404,
                "advanced_feature_snapshot_not_found",
                "Advanced feature snapshot not found",
            )
        return snapshot

    async def generate_for_signal(
        self,
        signal_id: UUID,
        force_recompute: bool = False,
    ) -> AdvancedFeatureSnapshot:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return await self.generate_for_analysis_run(signal.analysis_run_id, force_recompute)

    async def get_for_signal(self, signal_id: UUID) -> AdvancedFeatureSnapshot:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return await self.get_for_analysis_run(signal.analysis_run_id)

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return run

    async def add_audit_log(
        self,
        run: AnalysisRun,
        event_type: str,
        message: str,
        metadata_json: dict[str, object],
    ) -> None:
        await self.analysis_repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=run.id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )

    @property
    def feature_pack_version(self) -> str:
        return self.settings.advanced_feature_pack_version

    @property
    def calculator_settings(self) -> AdvancedFeatureCalculatorSettings:
        return AdvancedFeatureCalculatorSettings(
            min_candle_count=self.settings.advanced_feature_min_candle_count,
            swing_lookback=self.settings.advanced_feature_swing_lookback,
            zone_lookback=self.settings.advanced_feature_zone_lookback,
            compression_lookback=self.settings.advanced_feature_compression_lookback,
            expansion_multiplier=self.settings.advanced_feature_expansion_multiplier,
            wick_pressure_threshold=self.settings.advanced_feature_wick_pressure_threshold,
            movement_efficiency_threshold=(
                self.settings.advanced_feature_movement_efficiency_threshold
            ),
        )
