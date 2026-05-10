from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.analysis.repository import AnalysisRepository
from app.modules.features.repository import FeatureSnapshotRepository
from app.modules.indicators.repository import IndicatorSnapshotRepository
from app.modules.market_regimes.classifier import (
    MarketRegimeClassificationInput,
    MarketRegimeClassifier,
)
from app.modules.market_regimes.models import MarketRegimeContext
from app.modules.market_regimes.repository import MarketRegimeContextRepository
from app.modules.patterns.repository import PatternCandidateRepository
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository


class MarketRegimeContextService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = MarketRegimeContextRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.feature_repository = FeatureSnapshotRepository(session)
        self.indicator_repository = IndicatorSnapshotRepository(session)
        self.signal_repository = SignalRepository(session)
        self.pattern_repository = PatternCandidateRepository(session)
        self.classifier = MarketRegimeClassifier()

    async def generate_for_analysis_run(
        self,
        analysis_run_id: UUID,
        force_recompute: bool = False,
    ) -> MarketRegimeContext:
        existing = await self.repository.get_by_analysis_run_id(
            analysis_run_id,
            self.regime_version,
        )
        if existing is not None and not force_recompute:
            return existing
        analysis_run = await self.get_analysis_run(analysis_run_id)
        signal = await self.signal_repository.get_by_analysis_run_id(analysis_run_id)
        context = await self.build_context(analysis_run, signal)
        persisted = await self.repository.upsert_for_analysis_run(context, force_recompute)
        await self.add_audit_log(
            analysis_run.id,
            "market_regime_context_generated",
            "Market regime context generated",
            {
                "marketRegimeContextId": str(persisted.id),
                "regimeVersion": persisted.regime_version,
                "trendRegime": persisted.trend_regime,
                "volatilityRegime": persisted.volatility_regime,
                "rangeRegime": persisted.range_regime,
            },
        )
        await self.session.commit()
        return persisted

    async def generate_for_signal(
        self,
        signal_id: UUID,
        force_recompute: bool = False,
    ) -> MarketRegimeContext:
        signal = await self.get_signal(signal_id)
        existing = await self.repository.get_by_signal_id(signal_id, self.regime_version)
        if existing is not None and not force_recompute:
            return existing
        analysis_existing = await self.repository.get_by_analysis_run_id(
            signal.analysis_run_id,
            self.regime_version,
        )
        if analysis_existing is not None and not force_recompute:
            return analysis_existing
        analysis_run = await self.get_analysis_run(signal.analysis_run_id)
        context = await self.build_context(analysis_run, signal)
        persisted = await self.repository.upsert_for_analysis_run(context, force_recompute)
        await self.add_audit_log(
            analysis_run.id,
            "market_regime_context_generated",
            "Signal market regime context generated",
            {
                "marketRegimeContextId": str(persisted.id),
                "signalId": str(signal.id),
                "regimeVersion": persisted.regime_version,
            },
        )
        await self.session.commit()
        return persisted

    async def get_for_analysis_run(self, analysis_run_id: UUID) -> MarketRegimeContext:
        await self.get_analysis_run(analysis_run_id)
        context = await self.repository.get_by_analysis_run_id(analysis_run_id, self.regime_version)
        if context is None:
            raise AppError(
                404, "market_regime_context_not_found", "Market regime context not found"
            )
        return context

    async def get_for_signal(self, signal_id: UUID) -> MarketRegimeContext:
        signal = await self.get_signal(signal_id)
        context = await self.repository.get_by_signal_id(signal_id, self.regime_version)
        if context is None:
            context = await self.repository.get_by_analysis_run_id(
                signal.analysis_run_id,
                self.regime_version,
            )
        if context is None:
            raise AppError(
                404, "market_regime_context_not_found", "Market regime context not found"
            )
        return context

    async def build_context(
        self,
        analysis_run: AnalysisRun,
        signal: Signal | None,
    ) -> MarketRegimeContext:
        feature_snapshot = await self.feature_repository.get_by_analysis_run_id(analysis_run.id)
        indicator_snapshot = await self.indicator_repository.get_by_analysis_run_id(analysis_run.id)
        pattern_candidates = await self.pattern_repository.list_by_analysis_run_id(analysis_run.id)
        classification = self.classifier.classify(
            MarketRegimeClassificationInput(
                features_json=feature_snapshot.features_json if feature_snapshot else None,
                indicators_json=indicator_snapshot.indicators_json if indicator_snapshot else None,
                signal=signal,
                pattern_candidates=pattern_candidates,
                min_confidence=self.market_regime_min_confidence,
                strong_data_quality=self.market_regime_strong_data_quality,
                acceptable_data_quality=self.market_regime_acceptable_data_quality,
            )
        )
        metadata_json = {
            **classification.metadata_json,
            "analysisRunStatus": analysis_run.status,
            "analysisMode": analysis_run.analysis_mode,
            "featureSnapshotId": str(feature_snapshot.id) if feature_snapshot else None,
            "indicatorSnapshotId": str(indicator_snapshot.id) if indicator_snapshot else None,
        }
        return MarketRegimeContext(
            workspace_id=analysis_run.workspace_id,
            analysis_run_id=analysis_run.id,
            signal_id=signal.id if signal else None,
            symbol_id=analysis_run.symbol_id,
            timeframe=analysis_run.timeframe,
            regime_version=self.regime_version,
            trend_regime=classification.trend_regime.value,
            volatility_regime=classification.volatility_regime.value,
            range_regime=classification.range_regime.value,
            liquidity_regime=classification.liquidity_regime,
            data_quality_label=classification.data_quality_label.value,
            confidence_score=classification.confidence_score,
            confidence_label=classification.confidence_label.value,
            summary=classification.summary,
            feature_inputs_json=classification.feature_inputs_json,
            indicator_inputs_json=classification.indicator_inputs_json,
            warnings_json=classification.warnings_json,
            metadata_json=metadata_json,
        )

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun:
        analysis_run = await self.analysis_repository.get_run(analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return analysis_run

    async def get_signal(self, signal_id: UUID) -> Signal:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return signal

    async def add_audit_log(
        self,
        analysis_run_id: UUID,
        event_type: str,
        message: str,
        metadata_json: dict[str, object] | None = None,
    ) -> None:
        await self.analysis_repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=analysis_run_id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )

    @property
    def regime_version(self) -> str:
        return self.settings.market_regime_version

    @property
    def market_regime_min_confidence(self) -> Decimal:
        return self.settings.market_regime_min_confidence

    @property
    def market_regime_strong_data_quality(self) -> Decimal:
        return self.settings.market_regime_strong_data_quality

    @property
    def market_regime_acceptable_data_quality(self) -> Decimal:
        return self.settings.market_regime_acceptable_data_quality
