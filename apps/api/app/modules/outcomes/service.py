from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.analysis.repository import AnalysisRepository
from app.modules.candles.models import Candle
from app.modules.candles.service import CandleService
from app.modules.candles.timeframes import Timeframe
from app.modules.outcomes.aggregator import OutcomeAggregator
from app.modules.outcomes.calculator import (
    OUTCOME_EVALUATION_VERSION,
    OUTCOME_MIN_FUTURE_CANDLES,
    OutcomeCalculationInput,
    OutcomeCalculator,
    OutcomeCandle,
    OutcomeSymbolMetadata,
)
from app.modules.outcomes.models import (
    OutcomeEvaluationRun,
    OutcomeEvaluationRunStatus,
    OutcomeEvaluationScopeType,
    OutcomeEvaluationStatus,
    OutcomeLabel,
    SignalOutcome,
)
from app.modules.outcomes.repository import OutcomeRepository
from app.modules.outcomes.schemas import (
    OutcomeBackfillRequest,
    OutcomePerformanceQuery,
    OutcomePerformanceRead,
    normalize_horizons,
)
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository
from app.modules.symbols.repository import SymbolRepository


class OutcomeEvaluationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.outcome_repository = OutcomeRepository(session)
        self.signal_repository = SignalRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.candle_service = CandleService(session)
        self.calculator = OutcomeCalculator()
        self.aggregator = OutcomeAggregator()

    async def evaluate_signal_outcomes(
        self,
        signal_id: UUID,
        horizons_minutes: list[int] | None = None,
        force_recompute: bool = False,
    ) -> list[SignalOutcome]:
        signal = await self.get_signal(signal_id)
        run = await self.get_analysis_run(signal.analysis_run_id)
        horizons = self.resolve_horizons(horizons_minutes)
        await self.add_audit_log(
            run.id,
            "outcome_evaluation_requested",
            "Outcome evaluation requested",
            {"signalId": str(signal.id), "horizonsMinutes": horizons},
        )
        try:
            outcomes = [
                await self.evaluate_signal_horizon(
                    signal=signal,
                    run=run,
                    horizon_minutes=horizon,
                    force_recompute=force_recompute,
                )
                for horizon in horizons
            ]
            await self.add_audit_log(
                run.id,
                "outcome_evaluation_completed",
                "Outcome evaluation completed",
                {
                    "signalId": str(signal.id),
                    "outcomeCount": len(outcomes),
                    "horizonsMinutes": horizons,
                },
            )
            await self.session.commit()
            return outcomes
        except Exception:
            await self.session.rollback()
            await self.add_failure_audit_log(run.id, signal.id, horizons)
            await self.session.commit()
            raise

    async def get_signal_outcomes(self, signal_id: UUID) -> list[SignalOutcome]:
        await self.get_signal(signal_id)
        return await self.outcome_repository.list_by_signal_id(signal_id)

    async def get_signal_outcome(
        self,
        signal_id: UUID,
        horizon_minutes: int,
    ) -> SignalOutcome:
        await self.get_signal(signal_id)
        outcome = await self.outcome_repository.get_outcome_by_horizon(
            signal_id=signal_id,
            horizon_minutes=horizon_minutes,
        )
        if outcome is None:
            raise AppError(404, "signal_outcome_not_found", "Signal outcome not found")
        return outcome

    async def evaluate_analysis_run_outcomes(
        self,
        analysis_run_id: UUID,
        horizons_minutes: list[int] | None = None,
        force_recompute: bool = False,
    ) -> list[SignalOutcome]:
        run = await self.get_analysis_run(analysis_run_id)
        signal = await self.signal_repository.get_by_analysis_run_id(analysis_run_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        horizons = self.resolve_horizons(horizons_minutes)
        await self.add_audit_log(
            run.id,
            "outcome_evaluation_requested",
            "Analysis run outcome evaluation requested",
            {"signalId": str(signal.id), "horizonsMinutes": horizons},
        )
        return await self.evaluate_signal_outcomes(
            signal_id=signal.id,
            horizons_minutes=horizons,
            force_recompute=force_recompute,
        )

    async def get_analysis_run_outcomes(self, analysis_run_id: UUID) -> list[SignalOutcome]:
        await self.get_analysis_run(analysis_run_id)
        return await self.outcome_repository.list_by_analysis_run_id(analysis_run_id)

    async def backfill_outcomes(self, payload: OutcomeBackfillRequest) -> OutcomeEvaluationRun:
        horizons = self.resolve_horizons(payload.horizons_minutes)
        scope_type = (
            OutcomeEvaluationScopeType.SYMBOL_BACKFILL
            if payload.symbol_id is not None
            else OutcomeEvaluationScopeType.WORKSPACE_BACKFILL
        )
        run = await self.outcome_repository.create_evaluation_run(
            OutcomeEvaluationRun(
                workspace_id=payload.workspace_id,
                status=OutcomeEvaluationRunStatus.RUNNING,
                scope_type=scope_type,
                horizons_json=horizons,
                filters_json=payload.model_dump(mode="json", exclude={"horizons_minutes"}),
                started_at=datetime.now(UTC),
            )
        )
        signals: list[Signal] = []
        try:
            signals = await self.outcome_repository.list_backfill_signals(
                workspace_id=payload.workspace_id,
                symbol_id=payload.symbol_id,
                timeframe=payload.timeframe,
                include_replay=payload.include_replay,
                limit=payload.limit,
            )
            await self.add_workspace_backfill_audit_log(
                signals=signals,
                event_type="outcome_backfill_started",
                message="Outcome backfill started",
                metadata_json={"evaluationRunId": str(run.id), "signalCount": len(signals)},
            )
            evaluated_count = 0
            skipped_count = 0
            failed_count = 0
            for signal in signals:
                analysis_run = await self.analysis_repository.get_run(signal.analysis_run_id)
                if analysis_run is None:
                    failed_count += 1
                    continue
                for horizon in horizons:
                    outcome = await self.evaluate_signal_horizon(
                        signal=signal,
                        run=analysis_run,
                        horizon_minutes=horizon,
                        force_recompute=payload.force_recompute,
                    )
                    if outcome.evaluation_status == OutcomeEvaluationStatus.FAILED:
                        failed_count += 1
                    elif outcome.evaluation_status in {
                        OutcomeEvaluationStatus.INSUFFICIENT_FUTURE_DATA,
                        OutcomeEvaluationStatus.SKIPPED_NOT_DIRECTIONAL,
                    }:
                        skipped_count += 1
                    else:
                        evaluated_count += 1
            run.evaluated_count = evaluated_count
            run.skipped_count = skipped_count
            run.failed_count = failed_count
            run.completed_at = datetime.now(UTC)
            run.status = (
                OutcomeEvaluationRunStatus.COMPLETED_WITH_WARNINGS
                if failed_count or skipped_count
                else OutcomeEvaluationRunStatus.COMPLETED
            )
            await self.add_workspace_backfill_audit_log(
                signals=signals,
                event_type="outcome_backfill_completed",
                message="Outcome backfill completed",
                metadata_json={
                    "evaluationRunId": str(run.id),
                    "evaluatedCount": evaluated_count,
                    "skippedCount": skipped_count,
                    "failedCount": failed_count,
                },
            )
            await self.session.commit()
            return run
        except Exception as error:
            run.status = OutcomeEvaluationRunStatus.FAILED
            run.error_message = str(error)
            run.completed_at = datetime.now(UTC)
            await self.add_workspace_backfill_audit_log(
                signals=signals,
                event_type="outcome_backfill_failed",
                message="Outcome backfill failed",
                metadata_json={"evaluationRunId": str(run.id)},
            )
            await self.session.commit()
            raise

    async def get_evaluation_run(self, run_id: UUID) -> OutcomeEvaluationRun:
        run = await self.outcome_repository.get_evaluation_run(run_id)
        if run is None:
            raise AppError(
                404,
                "outcome_evaluation_run_not_found",
                "Outcome evaluation run not found",
            )
        return run

    async def aggregate_by_patterns(
        self,
        query: OutcomePerformanceQuery,
    ) -> list[OutcomePerformanceRead]:
        outcomes = await self.filtered_outcomes(query)
        return self.aggregator.aggregate_by_patterns(outcomes, query.horizon_minutes)

    async def aggregate_by_strategy_profiles(
        self,
        query: OutcomePerformanceQuery,
    ) -> list[OutcomePerformanceRead]:
        outcomes = await self.filtered_outcomes(query)
        return self.aggregator.aggregate_by_strategy_profiles(outcomes, query.horizon_minutes)

    async def aggregate_by_symbols(
        self,
        query: OutcomePerformanceQuery,
    ) -> list[OutcomePerformanceRead]:
        outcomes = await self.filtered_outcomes(query)
        return self.aggregator.aggregate_by_symbols(outcomes, query.horizon_minutes)

    async def evaluate_due_outcomes(self, limit: int) -> list[SignalOutcome]:
        if limit <= 0:
            return []
        return []

    async def evaluate_signal_horizon(
        self,
        signal: Signal,
        run: AnalysisRun,
        horizon_minutes: int,
        force_recompute: bool,
    ) -> SignalOutcome:
        existing = await self.outcome_repository.get_outcome(
            signal_id=signal.id,
            horizon_minutes=horizon_minutes,
            evaluation_version=self.evaluation_version,
        )
        if existing is not None and not force_recompute:
            await self.add_audit_log(
                run.id,
                "outcome_evaluation_skipped",
                "Existing outcome evaluation reused",
                {"signalId": str(signal.id), "horizonMinutes": horizon_minutes},
            )
            return existing
        await self.add_audit_log(
            run.id,
            "outcome_evaluation_started",
            "Outcome evaluation started",
            {"signalId": str(signal.id), "horizonMinutes": horizon_minutes},
        )
        symbol = await self.symbol_repository.get_by_id(signal.symbol_id)
        if symbol is None:
            outcome = self.failed_outcome(
                signal=signal,
                run=run,
                horizon_minutes=horizon_minutes,
                reason="symbol_not_found",
            )
            return await self.outcome_repository.upsert_outcome(outcome, force_recompute)
        reference = await self.reference_candle(run)
        if reference is None:
            outcome = self.failed_outcome(
                signal=signal,
                run=run,
                horizon_minutes=horizon_minutes,
                reason="reference_candle_not_found",
            )
            return await self.outcome_repository.upsert_outcome(outcome, force_recompute)
        future_window_start = reference.timestamp + timedelta(microseconds=1)
        future_window_end = run.end_time + timedelta(minutes=horizon_minutes)
        future_candles = await self.fetch_final_candles(
            run=run,
            start_time=future_window_start,
            end_time=future_window_end,
        )
        calculation = self.calculator.calculate(
            OutcomeCalculationInput(
                bias=signal.bias,
                classification_status=signal.classification_status,
                reference_price=reference.close,
                future_candles=[
                    OutcomeCandle(
                        timestamp=candle.timestamp,
                        high=candle.high,
                        low=candle.low,
                        close=candle.close,
                    )
                    for candle in future_candles
                ],
                symbol_metadata=OutcomeSymbolMetadata(
                    market_type=symbol.market_type,
                    pip_size=symbol.pip_size,
                    tick_size=symbol.tick_size,
                ),
                min_future_candles=self.min_future_candles,
            )
        )
        metadata_json = {
            **calculation.metadata_json,
            "referencePriceSource": "last_final_candle_at_or_before_analysis_end",
            "sourceAnalysisMode": run.analysis_mode,
            "replayedFromAnalysisRunId": (
                str(run.replayed_from_analysis_run_id)
                if run.replayed_from_analysis_run_id is not None
                else None
            ),
        }
        outcome = SignalOutcome(
            workspace_id=signal.workspace_id,
            analysis_run_id=signal.analysis_run_id,
            signal_id=signal.id,
            symbol_id=signal.symbol_id,
            timeframe=signal.timeframe,
            strategy_profile_key=signal.strategy_profile_key,
            strategy_profile_version=signal.strategy_profile_version,
            pattern_type=signal.pattern_type,
            bias=signal.bias,
            classification_status=signal.classification_status,
            horizon_minutes=horizon_minutes,
            evaluation_status=calculation.evaluation_status,
            reference_time=reference.timestamp,
            reference_price=reference.close,
            future_window_start=future_window_start,
            future_window_end=future_window_end,
            future_candle_count=calculation.future_candle_count,
            max_favorable_move=calculation.max_favorable_move,
            max_adverse_move=calculation.max_adverse_move,
            net_move=calculation.net_move,
            max_favorable_pips=calculation.max_favorable_pips,
            max_adverse_pips=calculation.max_adverse_pips,
            net_pips=calculation.net_pips,
            max_favorable_ticks=calculation.max_favorable_ticks,
            max_adverse_ticks=calculation.max_adverse_ticks,
            net_ticks=calculation.net_ticks,
            direction_followed=calculation.direction_followed,
            reversal_detected=calculation.reversal_detected,
            outcome_label=calculation.outcome_label,
            movement_quality=calculation.movement_quality,
            evaluation_version=self.evaluation_version,
            metadata_json=metadata_json,
        )
        persisted = await self.outcome_repository.upsert_outcome(outcome, force_recompute)
        await self.add_audit_log(
            run.id,
            "outcome_evaluation_completed",
            "Outcome evaluation horizon completed",
            {
                "signalId": str(signal.id),
                "horizonMinutes": horizon_minutes,
                "evaluationStatus": persisted.evaluation_status,
                "outcomeLabel": persisted.outcome_label,
            },
        )
        return persisted

    async def reference_candle(self, run: AnalysisRun) -> Candle | None:
        candles = await self.fetch_final_candles(
            run=run,
            start_time=run.start_time,
            end_time=run.end_time,
        )
        if candles:
            return candles[-1]
        return None

    async def fetch_final_candles(
        self,
        run: AnalysisRun,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Candle]:
        return await self.candle_service.fetch_candle_window(
            workspace_id=run.workspace_id,
            symbol_id=run.symbol_id,
            timeframe=Timeframe(run.timeframe),
            start_time=start_time,
            end_time=end_time,
            source_id=run.source_id,
            include_partial=False,
        )

    async def filtered_outcomes(self, query: OutcomePerformanceQuery) -> list[SignalOutcome]:
        return await self.outcome_repository.list_filtered_outcomes(
            workspace_id=query.workspace_id,
            symbol_id=query.symbol_id,
            timeframe=query.timeframe,
            horizon_minutes=query.horizon_minutes,
            pattern_type=query.pattern_type,
            strategy_profile_key=query.strategy_profile_key,
            start_time=query.start_time,
            end_time=query.end_time,
        )

    async def get_signal(self, signal_id: UUID) -> Signal:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return signal

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return run

    def failed_outcome(
        self,
        signal: Signal,
        run: AnalysisRun,
        horizon_minutes: int,
        reason: str,
    ) -> SignalOutcome:
        future_window_start = run.end_time + timedelta(microseconds=1)
        return SignalOutcome(
            workspace_id=signal.workspace_id,
            analysis_run_id=signal.analysis_run_id,
            signal_id=signal.id,
            symbol_id=signal.symbol_id,
            timeframe=signal.timeframe,
            strategy_profile_key=signal.strategy_profile_key,
            strategy_profile_version=signal.strategy_profile_version,
            pattern_type=signal.pattern_type,
            bias=signal.bias,
            classification_status=signal.classification_status,
            horizon_minutes=horizon_minutes,
            evaluation_status=OutcomeEvaluationStatus.FAILED,
            reference_time=run.end_time,
            reference_price=None,
            future_window_start=future_window_start,
            future_window_end=run.end_time + timedelta(minutes=horizon_minutes),
            future_candle_count=0,
            max_favorable_move=Decimal("0"),
            max_adverse_move=Decimal("0"),
            net_move=Decimal("0"),
            max_favorable_pips=None,
            max_adverse_pips=None,
            net_pips=None,
            max_favorable_ticks=None,
            max_adverse_ticks=None,
            net_ticks=None,
            direction_followed=None,
            reversal_detected=False,
            outcome_label=OutcomeLabel.FAILED,
            movement_quality=None,
            evaluation_version=self.evaluation_version,
            metadata_json={"failureReason": reason, "sourceAnalysisMode": run.analysis_mode},
        )

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

    async def add_failure_audit_log(
        self,
        analysis_run_id: UUID,
        signal_id: UUID,
        horizons: list[int],
    ) -> None:
        await self.add_audit_log(
            analysis_run_id,
            "outcome_evaluation_failed",
            "Outcome evaluation failed",
            {"signalId": str(signal_id), "horizonsMinutes": horizons},
        )

    async def add_workspace_backfill_audit_log(
        self,
        signals: list[Signal],
        event_type: str,
        message: str,
        metadata_json: dict[str, object],
    ) -> None:
        seen_analysis_run_ids: set[UUID] = set()
        for signal in signals:
            if signal.analysis_run_id in seen_analysis_run_ids:
                continue
            seen_analysis_run_ids.add(signal.analysis_run_id)
            await self.add_audit_log(signal.analysis_run_id, event_type, message, metadata_json)

    def resolve_horizons(self, horizons_minutes: list[int] | None) -> list[int]:
        if horizons_minutes is not None:
            return normalize_horizons(horizons_minutes)
        return normalize_horizons(self.settings.outcome_default_horizons_minutes)

    @property
    def min_future_candles(self) -> int:
        return self.settings.outcome_min_future_candles or OUTCOME_MIN_FUTURE_CANDLES

    @property
    def evaluation_version(self) -> str:
        return self.settings.outcome_evaluation_version or OUTCOME_EVALUATION_VERSION


class ScreenshotOutcomeAdapter:
    def linked_analysis_run_id(self, analysis_run_id: UUID | None) -> UUID | None:
        return analysis_run_id
