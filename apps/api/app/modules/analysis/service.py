from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.analysis.models import (
    AnalysisAuditLog,
    AnalysisMode,
    AnalysisRun,
    AnalysisRunStatus,
)
from app.modules.analysis.repository import AnalysisRepository
from app.modules.analysis.schemas import AnalysisRunCreate, LiveWindowAnalysisRunCreate
from app.modules.candles.models import Candle
from app.modules.candles.quality import CandleQualityReport
from app.modules.candles.service import CandleService
from app.modules.candles.timeframes import Timeframe, normalize_timestamp, timeframe_duration
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.features.models import FeatureSnapshot
from app.modules.features.service import FeatureSnapshotService
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.indicators.service import IndicatorSnapshotService
from app.modules.patterns.models import PatternCandidate
from app.modules.patterns.service import PatternCandidateService
from app.modules.signals.service import SignalClassificationService
from app.modules.symbols.repository import SymbolRepository

ANALYSIS_LIFECYCLE_ENGINE_VERSION = "analysis_lifecycle_0.1.0"
ANALYSIS_LIFECYCLE_RULE_SET_VERSION = "preflight_0.1.0"
DEFAULT_WARMUP_CANDLES = 100
DEFAULT_BASELINE_CANDLES = 60


class AnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AnalysisRepository(session)
        self.candle_service = CandleService(session)
        self.feature_snapshot_service = FeatureSnapshotService(session)
        self.indicator_snapshot_service = IndicatorSnapshotService(session)
        self.pattern_candidate_service = PatternCandidateService(session)
        self.signal_classification_service = SignalClassificationService(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def create_historical_run(self, payload: AnalysisRunCreate) -> AnalysisRun:
        start_time = normalize_timestamp(payload.start_time)
        end_time = normalize_timestamp(payload.end_time)
        await self.validate_request_boundary(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            start_time=start_time,
            end_time=end_time,
        )
        run = AnalysisRun(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            timeframe=payload.timeframe.value,
            start_time=start_time,
            end_time=end_time,
            warmup_start_time=self.resolve_window_start(
                payload.warmup_start_time,
                start_time,
                payload.timeframe,
                DEFAULT_WARMUP_CANDLES,
            ),
            baseline_start_time=self.resolve_window_start(
                payload.baseline_start_time,
                start_time,
                payload.timeframe,
                DEFAULT_BASELINE_CANDLES,
            ),
            analysis_mode=AnalysisMode.HISTORICAL,
            include_partial_live_candle=payload.include_partial_live_candle,
            include_news_correlation=payload.include_news_correlation,
            include_ai_explanation=payload.include_ai_explanation,
            status=AnalysisRunStatus.QUEUED,
            engine_version=ANALYSIS_LIFECYCLE_ENGINE_VERSION,
            rule_set_version=ANALYSIS_LIFECYCLE_RULE_SET_VERSION,
        )
        return await self.create_and_process_run(run)

    async def create_live_window_run(self, payload: LiveWindowAnalysisRunCreate) -> AnalysisRun:
        await self.validate_request_boundary(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            start_time=None,
            end_time=None,
        )
        latest_candle = await self.candle_service.get_latest_candle(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            timeframe=payload.timeframe,
            source_id=payload.source_id,
            is_final=None if payload.include_partial_live_candle else True,
        )
        end_time = latest_candle.timestamp
        start_time = end_time - timedelta(minutes=payload.lookback_minutes)
        run = AnalysisRun(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            timeframe=payload.timeframe.value,
            start_time=start_time,
            end_time=end_time,
            warmup_start_time=self.resolve_window_start(
                None,
                start_time,
                payload.timeframe,
                payload.warmup_candles or DEFAULT_WARMUP_CANDLES,
            ),
            baseline_start_time=self.resolve_window_start(
                None,
                start_time,
                payload.timeframe,
                payload.baseline_candles or DEFAULT_BASELINE_CANDLES,
            ),
            analysis_mode=AnalysisMode.LIVE_WINDOW,
            include_partial_live_candle=payload.include_partial_live_candle,
            include_news_correlation=payload.include_news_correlation,
            include_ai_explanation=payload.include_ai_explanation,
            status=AnalysisRunStatus.QUEUED,
            engine_version=ANALYSIS_LIFECYCLE_ENGINE_VERSION,
            rule_set_version=ANALYSIS_LIFECYCLE_RULE_SET_VERSION,
        )
        return await self.create_and_process_run(run)

    async def create_and_process_run(self, run: AnalysisRun) -> AnalysisRun:
        try:
            created_run = await self.repository.create_run(run)
            await self.add_audit_log(
                created_run.id,
                "analysis_created",
                "Analysis run created",
                {"analysisMode": created_run.analysis_mode},
            )
            await self.process_preflight(created_run)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "analysis_run_conflict",
                "Analysis run could not be created",
            ) from error
        except Exception:
            await self.session.rollback()
            raise
        return created_run

    async def list_runs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        symbol_id: UUID | None = None,
        status: str | None = None,
        analysis_mode: str | None = None,
    ) -> list[AnalysisRun]:
        return await self.repository.list_runs(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            status=status,
            analysis_mode=analysis_mode,
        )

    async def get_run(self, analysis_run_id: UUID) -> AnalysisRun:
        run = await self.repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return run

    async def list_audit_logs(self, analysis_run_id: UUID) -> list[AnalysisAuditLog]:
        await self.get_run(analysis_run_id)
        return await self.repository.list_audit_logs(analysis_run_id)

    async def get_feature_snapshot(self, analysis_run_id: UUID) -> FeatureSnapshot | None:
        await self.get_run(analysis_run_id)
        return await self.feature_snapshot_service.get_by_analysis_run_id(analysis_run_id)

    async def get_indicator_snapshot(self, analysis_run_id: UUID) -> IndicatorSnapshot | None:
        await self.get_run(analysis_run_id)
        return await self.indicator_snapshot_service.get_by_analysis_run_id(analysis_run_id)

    async def list_pattern_candidates(self, analysis_run_id: UUID) -> list[PatternCandidate]:
        await self.get_run(analysis_run_id)
        return await self.pattern_candidate_service.list_by_analysis_run_id(analysis_run_id)

    async def retry_run(self, analysis_run_id: UUID) -> AnalysisRun:
        run = await self.get_run(analysis_run_id)
        if run.status not in {
            AnalysisRunStatus.FAILED,
            AnalysisRunStatus.INSUFFICIENT_DATA,
            AnalysisRunStatus.CANCELLED,
        }:
            raise AppError(
                422,
                "analysis_run_not_retryable",
                "Only failed, insufficient_data, or cancelled runs can be retried",
            )
        try:
            run.status = AnalysisRunStatus.QUEUED
            run.error_code = None
            run.error_message = None
            run.started_at = None
            run.completed_at = None
            await self.add_audit_log(
                run.id,
                "analysis_retry_queued",
                "Analysis run queued for retry",
            )
            await self.process_preflight(run)
            await self.session.commit()
            return run
        except Exception:
            await self.session.rollback()
            raise

    async def process_preflight(self, run: AnalysisRun) -> None:
        run.status = AnalysisRunStatus.RUNNING
        run.started_at = utc_now()
        run.completed_at = None
        await self.add_audit_log(run.id, "analysis_running", "Analysis lifecycle preflight started")
        try:
            analysis_candles = await self.load_analysis_candles(run)
            quality_report = await self.candle_service.calculate_window_quality(
                workspace_id=run.workspace_id,
                symbol_id=run.symbol_id,
                timeframe=Timeframe(run.timeframe),
                start_time=run.start_time,
                end_time=run.end_time,
                source_id=run.source_id,
            )
            await self.add_audit_log(
                run.id,
                "candles_loaded",
                "Analysis candles loaded",
                {
                    "analysisCandleCount": len(analysis_candles),
                    "dataQuality": quality_report.model_dump(mode="json"),
                },
            )
            warmup_candles = await self.load_auxiliary_window(run, run.warmup_start_time)
            baseline_candles = await self.load_auxiliary_window(run, run.baseline_start_time)
            await self.add_audit_log(
                run.id,
                "analysis_windows_resolved",
                "Warmup and baseline windows resolved",
                {
                    "warmupCandleCount": len(warmup_candles),
                    "baselineCandleCount": len(baseline_candles),
                },
            )
            if not self.has_sufficient_data(run, analysis_candles, quality_report):
                self.mark_insufficient_data(run, quality_report)
                await self.add_audit_log(
                    run.id,
                    "insufficient_data",
                    "Analysis window does not contain enough final candle data",
                    {"dataQuality": quality_report.model_dump(mode="json")},
                )
                return
            feature_snapshot = await self.feature_snapshot_service.create_snapshot(
                analysis_run=run,
                analysis_candles=analysis_candles,
                warmup_candles=warmup_candles,
                baseline_candles=baseline_candles,
                data_quality=quality_report,
            )
            await self.add_audit_log(
                run.id,
                "features_calculated",
                "Feature snapshot calculated and persisted",
                {"featureSnapshotId": str(feature_snapshot.id)},
            )
            indicator_snapshot = await self.indicator_snapshot_service.create_snapshot(
                analysis_run=run,
                analysis_candles=analysis_candles,
                warmup_candles=warmup_candles,
                baseline_candles=baseline_candles,
            )
            await self.add_audit_log(
                run.id,
                "indicators_calculated",
                "Indicator snapshot calculated and persisted",
                {
                    "indicatorSnapshotId": str(indicator_snapshot.id),
                    "isReady": indicator_snapshot_is_ready(
                        indicator_snapshot.indicators_json
                    ),
                },
            )
            pattern_candidates = await self.pattern_candidate_service.create_candidates(
                analysis_run=run,
                analysis_candles=analysis_candles,
                baseline_candles=baseline_candles,
                feature_snapshot=feature_snapshot,
                indicator_snapshot=indicator_snapshot,
            )
            selected_candidate = next(
                (candidate for candidate in pattern_candidates if candidate.is_selected),
                None,
            )
            await self.add_audit_log(
                run.id,
                "patterns_detected",
                "Pattern candidates calculated and persisted",
                {
                    "candidateCount": len(pattern_candidates),
                    "selectedPatternCandidateId": (
                        str(selected_candidate.id) if selected_candidate is not None else None
                    ),
                    "selectedPatternType": (
                        selected_candidate.pattern_type
                        if selected_candidate is not None
                        else None
                    ),
                },
            )
            signal = await self.signal_classification_service.classify_run(
                run,
                require_completed=False,
            )
            await self.add_audit_log(
                run.id,
                "signals_calculated",
                "Deterministic signal classification completed and persisted",
                {
                    "signalId": str(signal.id),
                    "classificationStatus": signal.classification_status,
                    "bias": signal.bias,
                    "strategyProfileKey": signal.strategy_profile_key,
                },
            )
            run.status = AnalysisRunStatus.COMPLETED
            run.completed_at = utc_now()
            await self.add_audit_log(
                run.id,
                "analysis_completed",
                (
                    "Analysis feature, indicator, pattern, and signal classification "
                    "artifacts completed"
                ),
            )
        except AppError as error:
            run.status = AnalysisRunStatus.FAILED
            run.error_code = error.code
            run.error_message = error.message
            run.completed_at = utc_now()
            await self.add_audit_log(
                run.id,
                "analysis_failed",
                "Analysis lifecycle preflight failed",
                {"errorCode": error.code, "errorMessage": error.message},
            )

    async def load_analysis_candles(self, run: AnalysisRun) -> list[Candle]:
        return await self.candle_service.fetch_candle_window(
            workspace_id=run.workspace_id,
            symbol_id=run.symbol_id,
            timeframe=Timeframe(run.timeframe),
            start_time=run.start_time,
            end_time=run.end_time,
            source_id=run.source_id,
            include_partial=run.include_partial_live_candle,
        )

    async def load_auxiliary_window(
        self,
        run: AnalysisRun,
        window_start_time: datetime | None,
    ) -> list[Candle]:
        if window_start_time is None:
            return []
        window_end_time = run.start_time - timeframe_duration(Timeframe(run.timeframe))
        if window_start_time > window_end_time:
            return []
        return await self.candle_service.fetch_candle_window(
            workspace_id=run.workspace_id,
            symbol_id=run.symbol_id,
            timeframe=Timeframe(run.timeframe),
            start_time=window_start_time,
            end_time=window_end_time,
            source_id=run.source_id,
            include_partial=False,
        )

    def has_sufficient_data(
        self,
        run: AnalysisRun,
        analysis_candles: list[Candle],
        quality_report: CandleQualityReport,
    ) -> bool:
        if not analysis_candles or quality_report.expected_candles == 0:
            return False
        if quality_report.duplicate_candles > 0:
            return False
        if quality_report.missing_candles == 0:
            return True
        return bool(
            run.include_partial_live_candle
            and quality_report.missing_candles == 1
            and quality_report.has_partial_latest_candle
        )

    def mark_insufficient_data(
        self,
        run: AnalysisRun,
        quality_report: CandleQualityReport,
    ) -> None:
        run.status = AnalysisRunStatus.INSUFFICIENT_DATA
        run.error_code = "insufficient_candle_data"
        run.error_message = "Analysis window does not contain enough final candle data"
        run.completed_at = utc_now()

    async def validate_request_boundary(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> None:
        if start_time is not None and end_time is not None and start_time > end_time:
            raise AppError(422, "invalid_analysis_window", "start_time must be before end_time")
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if not symbol.is_active:
            raise AppError(422, "inactive_symbol", "Inactive symbols cannot be analyzed")
        if source_id is None:
            return
        data_source = await self.data_source_repository.get_by_id(source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if data_source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )

    def resolve_window_start(
        self,
        requested_start_time: datetime | None,
        analysis_start_time: datetime,
        timeframe: Timeframe,
        candle_count: int,
    ) -> datetime | None:
        if requested_start_time is not None:
            return normalize_timestamp(requested_start_time)
        if candle_count == 0:
            return None
        return analysis_start_time - (timeframe_duration(timeframe) * candle_count)

    async def add_audit_log(
        self,
        analysis_run_id: UUID,
        event_type: str,
        message: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> AnalysisAuditLog:
        return await self.repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=analysis_run_id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )


def indicator_snapshot_is_ready(indicators_json: Mapping[str, object]) -> object:
    calculation = indicators_json.get("calculation")
    if isinstance(calculation, Mapping):
        return calculation.get("isReady")
    return None
