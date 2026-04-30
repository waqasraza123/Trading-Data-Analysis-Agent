from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.analysis.models import AnalysisRun, AnalysisRunStatus
from app.modules.analysis.schemas import AnalysisRunCreate, AnalysisRunRead
from app.modules.analysis.service import AnalysisService
from app.modules.candles.models import Candle
from app.modules.candles.normalizer import RawCandlePayload, normalize_candle_payload
from app.modules.candles.quality import CandleQualityReport
from app.modules.candles.repository import CandleRepository
from app.modules.candles.schemas import CandleOriginType, CandleRead, CandleUpsertStatus
from app.modules.candles.service import CandleService
from app.modules.candles.timeframes import Timeframe
from app.modules.candles.validator import validate_candle
from app.modules.chart_screenshots.models import (
    ChartScreenshotRun,
    ChartScreenshotRunStatus,
    ChartTrendDirection,
)
from app.modules.chart_screenshots.parser import (
    CHART_SCREENSHOT_PARSER_NAME,
    CHART_SCREENSHOT_PARSER_VERSION,
    build_trend_hypothesis,
)
from app.modules.chart_screenshots.repository import ChartScreenshotRunRepository
from app.modules.chart_screenshots.schemas import (
    ChartScreenshotDecisionRead,
    ChartScreenshotLineageRead,
    ChartScreenshotPredictionCreate,
    ChartScreenshotReportRead,
    ChartScreenshotReviewStatus,
    ChartScreenshotRunRead,
    ChartScreenshotRunReviewRead,
    ChartScreenshotRunReviewRequest,
)
from app.modules.data_sources.models import DataSource, DataSourceType
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.signals.schemas import SignalClassificationRead
from app.modules.signals.service import SignalClassificationService
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository


class ChartScreenshotPredictionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ChartScreenshotRunRepository(session)
        self.candle_repository = CandleRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def create_prediction_run(
        self,
        payload: ChartScreenshotPredictionCreate,
    ) -> ChartScreenshotRun:
        try:
            symbol, data_source = await self.resolve_symbol_and_source(payload)
            hypothesis = build_trend_hypothesis(payload.candles, payload.extraction_confidence)
            now = utc_now()
            run = await self.repository.create(
                ChartScreenshotRun(
                    workspace_id=payload.workspace_id,
                    user_id=payload.user_id,
                    source_id=payload.source_id,
                    symbol_id=payload.symbol_id,
                    analysis_run_id=None,
                    timeframe=payload.timeframe.value,
                    file_name=payload.file_name,
                    parser_name=payload.parser_name or CHART_SCREENSHOT_PARSER_NAME,
                    parser_version=payload.parser_version or CHART_SCREENSHOT_PARSER_VERSION,
                    parser_source_path=payload.parser_source_path,
                    status=ChartScreenshotRunStatus.PARSING.value,
                    extraction_confidence=payload.extraction_confidence,
                    raw_candle_count=len(payload.candles),
                    stored_candle_count=0,
                    duplicate_count=0,
                    conflict_count=0,
                    analysis_hypothesis=hypothesis.direction.value,
                    analysis_hypothesis_confidence=hypothesis.confidence,
                    extracted_window_start=min(candle.timestamp for candle in payload.candles),
                    extracted_window_end=max(candle.timestamp for candle in payload.candles),
                    extracted_payload_json={
                        "candles": [candle.model_dump(mode="json") for candle in payload.candles],
                        "trendMetrics": hypothesis.metrics_json,
                    },
                    extraction_warnings_json={"warnings": hypothesis.warnings},
                    parser_metadata_json=payload.parser_metadata_json,
                    started_at=now,
                )
            )
            await self.store_extracted_candles(
                run=run,
                payload=payload,
                symbol=symbol,
                data_source=data_source,
            )
            self.finalize_run(run)
            await self.session.commit()
            await self.session.refresh(run)
            if payload.trigger_analysis:
                run = await self.trigger_analysis_for_run(run.id, payload)
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "chart_screenshot_run_conflict",
                "Chart screenshot prediction run could not be created",
            ) from error
        except Exception:
            await self.session.rollback()
            raise
        return run

    async def trigger_analysis_for_run(
        self,
        run_id: UUID,
        payload: ChartScreenshotPredictionCreate,
    ) -> ChartScreenshotRun:
        run = await self.get_run(run_id)
        if run.status == ChartScreenshotRunStatus.FAILED.value:
            return run
        if run.extracted_window_start is None or run.extracted_window_end is None:
            run.status = ChartScreenshotRunStatus.ANALYSIS_FAILED.value
            run.last_error_code = "chart_screenshot_window_missing"
            run.last_error_message = "Chart screenshot run has no extracted analysis window"
            await self.session.commit()
            await self.session.refresh(run)
            return run
        analysis_service = AnalysisService(self.session)
        try:
            analysis_run = await analysis_service.create_historical_run(
                AnalysisRunCreate(
                    workspace_id=run.workspace_id,
                    user_id=run.user_id,
                    symbol_id=run.symbol_id,
                    source_id=run.source_id,
                    timeframe=payload.timeframe,
                    start_time=run.extracted_window_start,
                    end_time=run.extracted_window_end,
                    warmup_start_time=payload.analysis_warmup_start_time,
                    baseline_start_time=payload.analysis_baseline_start_time,
                    include_news_correlation=payload.include_news_correlation,
                    include_ai_explanation=payload.include_ai_explanation,
                )
            )
        except AppError as error:
            await self.session.rollback()
            latest_run = await self.get_run(run.id)
            latest_run.status = ChartScreenshotRunStatus.ANALYSIS_FAILED.value
            latest_run.last_error_code = error.code
            latest_run.last_error_message = error.message
            await self.session.commit()
            await self.session.refresh(latest_run)
            return latest_run
        latest_run = await self.get_run(run.id)
        latest_run.analysis_run_id = analysis_run.id
        latest_run.status = ChartScreenshotRunStatus.ANALYSIS_TRIGGERED.value
        latest_run.parser_metadata_json = {
            **latest_run.parser_metadata_json,
            "analysisTrigger": {
                "analysisRunId": str(analysis_run.id),
                "analysisStatus": str(analysis_run.status),
                "includeNewsCorrelation": payload.include_news_correlation,
                "includeAiExplanation": payload.include_ai_explanation,
            },
        }
        await self.session.commit()
        await self.session.refresh(latest_run)
        return latest_run

    async def get_run(self, run_id: UUID) -> ChartScreenshotRun:
        run = await self.repository.get_by_id(run_id)
        if run is None:
            raise AppError(404, "chart_screenshot_run_not_found", "Chart screenshot run not found")
        return run

    async def review_run(
        self,
        run_id: UUID,
        payload: ChartScreenshotRunReviewRequest,
    ) -> ChartScreenshotRunReviewRead:
        original_run = await self.get_run(run_id)
        corrected_run: ChartScreenshotRun | None = None
        if payload.review_status == ChartScreenshotReviewStatus.CORRECTED:
            if not payload.corrected_candles:
                raise AppError(
                    422,
                    "corrected_candles_required",
                    "Corrected review status requires corrected_candles",
                )
            corrected_run = await self.create_correction_run(original_run, payload)
            original_run = await self.get_run(run_id)
        elif payload.corrected_candles:
            raise AppError(
                422,
                "invalid_review_correction",
                "corrected_candles can only be provided when review_status is corrected",
            )
        if payload.trigger_analysis and payload.review_status not in {
            ChartScreenshotReviewStatus.ACCEPTED,
            ChartScreenshotReviewStatus.CORRECTED,
        }:
            raise AppError(
                422,
                "invalid_review_analysis_trigger",
                "Only accepted or corrected reviews can trigger analysis",
            )
        if (
            payload.review_status == ChartScreenshotReviewStatus.ACCEPTED
            and payload.trigger_analysis
            and original_run.analysis_run_id is None
        ):
            original_run = await self.trigger_analysis_for_reviewed_run(original_run, payload)
        original_run.parser_metadata_json = self.with_human_review_metadata(
            original_run.parser_metadata_json,
            payload,
            corrected_run,
        )
        await self.session.commit()
        await self.session.refresh(original_run)
        if corrected_run is not None:
            await self.session.refresh(corrected_run)
        return ChartScreenshotRunReviewRead(
            reviewed_run=ChartScreenshotRunRead.model_validate(original_run),
            corrected_run=(
                ChartScreenshotRunRead.model_validate(corrected_run)
                if corrected_run is not None
                else None
            ),
        )

    async def get_decision(self, run_id: UUID) -> ChartScreenshotDecisionRead:
        run = await self.get_run(run_id)
        warnings = self.extract_warning_items(run.extraction_warnings_json)
        limitations = [
            "Chart screenshot outputs are hypotheses, not financial advice or trade instructions",
            "Image-derived candles depend on extraction quality and supplied calibration metadata",
        ]
        if run.analysis_run_id is None:
            warnings.append("No linked analysis run exists; returning screenshot-only hypothesis")
            return self.build_screenshot_hypothesis_decision(
                run=run,
                warnings=warnings,
                limitations=limitations,
            )
        analysis_service = AnalysisService(self.session)
        analysis_run = await analysis_service.get_run(run.analysis_run_id)
        if analysis_run.status != AnalysisRunStatus.COMPLETED.value:
            warnings.append(
                "Linked analysis run is "
                f"{analysis_run.status}; returning screenshot-only hypothesis"
            )
            return self.build_screenshot_hypothesis_decision(
                run=run,
                warnings=warnings,
                limitations=limitations,
                analysis_run=analysis_run,
            )
        try:
            signal_classification = await SignalClassificationService(
                self.session
            ).get_by_analysis_run_id(analysis_run.id)
        except AppError as error:
            if error.code != "signal_not_found":
                raise
            warnings.append("Linked analysis run completed without a persisted signal")
            return self.build_screenshot_hypothesis_decision(
                run=run,
                warnings=warnings,
                limitations=limitations,
                analysis_run=analysis_run,
            )
        reasoning = self.build_analysis_reasoning(signal_classification)
        return ChartScreenshotDecisionRead(
            chart_screenshot_run=ChartScreenshotRunRead.model_validate(run),
            decision_source="deterministic_analysis",
            direction=ChartTrendDirection(signal_classification.signal.bias.value),
            confidence=signal_classification.signal.confidence_score,
            confidence_label=signal_classification.signal.confidence_label.value,
            reasoning=reasoning,
            warnings=warnings,
            limitations=limitations,
            analysis_status=AnalysisRunStatus(analysis_run.status),
            analysis_run=AnalysisRunRead.model_validate(analysis_run),
            signal_classification=signal_classification,
        )

    async def get_report(self, run_id: UUID) -> ChartScreenshotReportRead:
        run = await self.get_run(run_id)
        stored_candles = await self.candle_repository.list_by_chart_screenshot_run_id(run.id)
        candle_quality = self.build_report_quality(run, stored_candles)
        decision = await self.get_decision(run.id)
        review_metadata = object_dict(run.parser_metadata_json.get("humanReview"))
        correction_run = await self.resolve_correction_run(review_metadata)
        corrected_from_run_id = parse_optional_uuid(
            run.parser_metadata_json.get("correctedFromChartScreenshotRunId")
        )
        return ChartScreenshotReportRead(
            chart_screenshot_run=ChartScreenshotRunRead.model_validate(run),
            stored_candles=[CandleRead.model_validate(candle) for candle in stored_candles],
            candle_quality=candle_quality,
            decision=decision,
            review_metadata_json=review_metadata,
            correction_run=(
                ChartScreenshotRunRead.model_validate(correction_run)
                if correction_run is not None
                else None
            ),
            corrected_from_run_id=corrected_from_run_id,
            trend_metrics_json=self.extract_trend_metrics(run),
            parser_tuning_json=object_dict(run.parser_metadata_json.get("parserTuning")),
            audit_warnings=self.extract_warning_items(run.extraction_warnings_json),
            report_limitations=[
                "Report data is an audit bundle of persisted backend artifacts",
                "Stored candles only include candles linked directly to this chart screenshot run",
                "Duplicate candles may be counted on the run without being linked to this run",
                "Outputs are market-analysis artifacts, not financial advice or trade instructions",
            ],
        )

    async def get_lineage(self, run_id: UUID) -> ChartScreenshotLineageRead:
        requested_run = await self.get_run(run_id)
        lineage_warnings: list[str] = []
        parent_run = await self.resolve_parent_run(requested_run, lineage_warnings)
        root_run = await self.resolve_root_run(requested_run, lineage_warnings)
        correction_runs = await self.collect_correction_runs(root_run.id, lineage_warnings)
        latest_correction_run = correction_runs[-1] if correction_runs else None
        recommended_run = latest_correction_run or root_run
        recommended_decision = await self.get_decision(recommended_run.id)
        return ChartScreenshotLineageRead(
            requested_run=ChartScreenshotRunRead.model_validate(requested_run),
            root_run=ChartScreenshotRunRead.model_validate(root_run),
            parent_run=(
                ChartScreenshotRunRead.model_validate(parent_run)
                if parent_run is not None
                else None
            ),
            correction_runs=[ChartScreenshotRunRead.model_validate(run) for run in correction_runs],
            latest_correction_run=(
                ChartScreenshotRunRead.model_validate(latest_correction_run)
                if latest_correction_run is not None
                else None
            ),
            recommended_run=ChartScreenshotRunRead.model_validate(recommended_run),
            recommended_decision=recommended_decision,
            lineage_warnings=lineage_warnings,
        )

    async def list_runs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        symbol_id: UUID | None = None,
        source_id: UUID | None = None,
        status: ChartScreenshotRunStatus | None = None,
    ) -> list[ChartScreenshotRun]:
        return await self.repository.list_runs(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            status=status.value if status is not None else None,
        )

    async def resolve_symbol_and_source(
        self,
        payload: ChartScreenshotPredictionCreate,
    ) -> tuple[Symbol, DataSource]:
        symbol = await self.symbol_repository.get_by_id(payload.symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        data_source = await self.data_source_repository.get_by_id(payload.source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if data_source.workspace_id != payload.workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )
        if data_source.source_type != DataSourceType.CHART_SCREENSHOT.value:
            raise AppError(
                422,
                "invalid_chart_screenshot_source",
                "Chart screenshot runs require a chart_screenshot data source",
            )
        return symbol, data_source

    async def store_extracted_candles(
        self,
        run: ChartScreenshotRun,
        payload: ChartScreenshotPredictionCreate,
        symbol: Symbol,
        data_source: DataSource,
    ) -> None:
        raw_warning_items = run.extraction_warnings_json.get("warnings")
        warning_items = (
            [str(item) for item in raw_warning_items] if isinstance(raw_warning_items, list) else []
        )
        stored_count = 0
        duplicate_count = 0
        conflict_count = 0
        for row_number, candle in enumerate(
            sorted(payload.candles, key=lambda item: item.timestamp),
            start=1,
        ):
            try:
                normalized_candle = normalize_candle_payload(
                    payload=RawCandlePayload.model_validate(candle.model_dump(mode="python")),
                    workspace_id=payload.workspace_id,
                    symbol_id=payload.symbol_id,
                    source_id=payload.source_id,
                    timeframe=payload.timeframe,
                    is_final=True,
                    origin_type=CandleOriginType.CHART_SCREENSHOT,
                    origin_reference_id=run.id,
                )
            except (AppError, ValidationError) as error:
                warning_items.append(self.format_candle_error(row_number, error))
                continue
            validation_result = validate_candle(
                candle=normalized_candle,
                symbol=symbol,
                data_source=data_source,
            )
            if not validation_result.is_valid:
                for issue in validation_result.issues:
                    warning_items.append(f"row {row_number}: {issue.code.value}: {issue.message}")
                continue
            upsert_result = await self.candle_repository.upsert_normalized_candle(
                normalized_candle,
            )
            if upsert_result.status in {
                CandleUpsertStatus.INSERTED,
                CandleUpsertStatus.UPDATED_PARTIAL,
                CandleUpsertStatus.FINALIZED,
            }:
                stored_count += 1
            elif upsert_result.status in {
                CandleUpsertStatus.DUPLICATE_FINAL,
                CandleUpsertStatus.IGNORED_LATE_PARTIAL,
            }:
                duplicate_count += 1
            elif upsert_result.status == CandleUpsertStatus.CONFLICTING_FINAL:
                conflict_count += 1
                warning_items.append(f"row {row_number}: conflicting_final_candle")
        run.stored_candle_count = stored_count
        run.duplicate_count = duplicate_count
        run.conflict_count = conflict_count
        run.extraction_warnings_json = {"warnings": warning_items}

    def finalize_run(self, run: ChartScreenshotRun) -> None:
        if run.stored_candle_count == 0 and run.duplicate_count == 0:
            run.status = ChartScreenshotRunStatus.FAILED.value
            run.analysis_hypothesis = ChartTrendDirection.UNCLEAR.value
            run.analysis_hypothesis_confidence = Decimal("0.0000")
            run.last_error_code = "no_extracted_candles_stored"
            run.last_error_message = "No extracted screenshot candles could be stored"
        else:
            run.status = ChartScreenshotRunStatus.COMPLETED.value
        run.completed_at = utc_now()

    def format_candle_error(self, row_number: int, error: Exception) -> str:
        if isinstance(error, AppError):
            return f"row {row_number}: {error.code}: {error.message}"
        if isinstance(error, ValidationError):
            first_error = error.errors()[0]
            return f"row {row_number}: invalid_row: {first_error['msg']}"
        return f"row {row_number}: invalid_row"

    def build_screenshot_hypothesis_decision(
        self,
        run: ChartScreenshotRun,
        warnings: list[str],
        limitations: list[str],
        analysis_run: AnalysisRun | None = None,
    ) -> ChartScreenshotDecisionRead:
        trend_metrics = {}
        if run.extracted_payload_json is not None:
            raw_metrics = run.extracted_payload_json.get("trendMetrics")
            if isinstance(raw_metrics, dict):
                trend_metrics = raw_metrics
        return ChartScreenshotDecisionRead(
            chart_screenshot_run=ChartScreenshotRunRead.model_validate(run),
            decision_source="chart_screenshot_hypothesis",
            direction=ChartTrendDirection(run.analysis_hypothesis),
            confidence=run.analysis_hypothesis_confidence,
            confidence_label=None,
            reasoning=self.build_screenshot_reasoning(run, trend_metrics),
            warnings=warnings,
            limitations=limitations,
            analysis_status=(
                AnalysisRunStatus(analysis_run.status) if analysis_run is not None else None
            ),
            analysis_run=(
                AnalysisRunRead.model_validate(analysis_run) if analysis_run is not None else None
            ),
            signal_classification=None,
        )

    def build_screenshot_reasoning(
        self,
        run: ChartScreenshotRun,
        trend_metrics: dict[str, object],
    ) -> list[str]:
        reasoning = [
            f"Screenshot hypothesis is {run.analysis_hypothesis} with confidence "
            f"{run.analysis_hypothesis_confidence}.",
            f"Stored {run.stored_candle_count} extracted candles, with "
            f"{run.duplicate_count} duplicates and {run.conflict_count} conflicts.",
        ]
        if trend_metrics:
            reasoning.append(
                "Trend metrics: "
                f"firstClose={trend_metrics.get('firstClose')}, "
                f"lastClose={trend_metrics.get('lastClose')}, "
                f"moveRatio={trend_metrics.get('moveRatio')}, "
                f"upwardSteps={trend_metrics.get('upwardSteps')}, "
                f"downwardSteps={trend_metrics.get('downwardSteps')}, "
                f"closeConsistency={trend_metrics.get('closeConsistency')}."
            )
        return reasoning

    def build_analysis_reasoning(
        self,
        signal_classification: SignalClassificationRead,
    ) -> list[str]:
        signal = signal_classification.signal
        reasoning = [signal.summary]
        explanation = signal_classification.deterministic_explanation
        if explanation is not None:
            reasoning.extend(
                [
                    explanation.short_summary,
                    explanation.evidence_summary,
                    explanation.confidence_summary,
                    explanation.risk_summary,
                ]
            )
        if signal_classification.evidence:
            reasoning.extend(item.message for item in signal_classification.evidence[:5])
        return [item for item in reasoning if item]

    def extract_warning_items(self, warnings_json: dict[str, object]) -> list[str]:
        raw_warnings = warnings_json.get("warnings")
        if not isinstance(raw_warnings, list):
            return []
        return [str(item) for item in raw_warnings]

    def build_report_quality(
        self,
        run: ChartScreenshotRun,
        stored_candles: list[Candle],
    ) -> CandleQualityReport | None:
        if run.extracted_window_start is None or run.extracted_window_end is None:
            return None
        return CandleService(self.session).calculate_quality_report(
            candles=stored_candles,
            timeframe=Timeframe(run.timeframe),
            start_time=run.extracted_window_start,
            end_time=run.extracted_window_end,
        )

    async def resolve_correction_run(
        self,
        review_metadata: dict[str, object] | None,
    ) -> ChartScreenshotRun | None:
        if review_metadata is None:
            return None
        correction_run_id = parse_optional_uuid(
            review_metadata.get("correctedChartScreenshotRunId")
        )
        if correction_run_id is None:
            return None
        return await self.repository.get_by_id(correction_run_id)

    async def resolve_parent_run(
        self,
        run: ChartScreenshotRun,
        lineage_warnings: list[str],
    ) -> ChartScreenshotRun | None:
        parent_run_id = parse_optional_uuid(
            run.parser_metadata_json.get("correctedFromChartScreenshotRunId")
        )
        if parent_run_id is None:
            return None
        parent_run = await self.repository.get_by_id(parent_run_id)
        if parent_run is None:
            lineage_warnings.append(
                f"Parent correction run {parent_run_id} was referenced but not found"
            )
        return parent_run

    async def resolve_root_run(
        self,
        run: ChartScreenshotRun,
        lineage_warnings: list[str],
    ) -> ChartScreenshotRun:
        current_run = run
        visited_run_ids: set[UUID] = set()
        while True:
            if current_run.id in visited_run_ids:
                lineage_warnings.append("Correction lineage loop detected")
                return current_run
            visited_run_ids.add(current_run.id)
            parent_run = await self.resolve_parent_run(current_run, lineage_warnings)
            if parent_run is None:
                return current_run
            current_run = parent_run

    async def collect_correction_runs(
        self,
        root_run_id: UUID,
        lineage_warnings: list[str],
    ) -> list[ChartScreenshotRun]:
        correction_runs: list[ChartScreenshotRun] = []
        visited_run_ids: set[UUID] = {root_run_id}
        pending_run_ids: list[UUID] = [root_run_id]
        while pending_run_ids:
            current_run_id = pending_run_ids.pop(0)
            direct_corrections = await self.repository.list_by_parser_source_path(
                f"correction:{current_run_id}"
            )
            for correction_run in direct_corrections:
                if correction_run.id in visited_run_ids:
                    lineage_warnings.append(
                        f"Correction lineage loop skipped at {correction_run.id}"
                    )
                    continue
                visited_run_ids.add(correction_run.id)
                correction_runs.append(correction_run)
                pending_run_ids.append(correction_run.id)
        correction_runs.sort(key=lambda run: run.created_at)
        return correction_runs

    def extract_trend_metrics(self, run: ChartScreenshotRun) -> dict[str, object]:
        if run.extracted_payload_json is None:
            return {}
        raw_metrics = run.extracted_payload_json.get("trendMetrics")
        return object_dict(raw_metrics) or {}

    async def create_correction_run(
        self,
        original_run: ChartScreenshotRun,
        payload: ChartScreenshotRunReviewRequest,
    ) -> ChartScreenshotRun:
        if payload.corrected_candles is None:
            raise AppError(
                422,
                "corrected_candles_required",
                "Corrected review status requires corrected_candles",
            )
        correction_payload = ChartScreenshotPredictionCreate(
            workspace_id=original_run.workspace_id,
            user_id=payload.reviewer_user_id or original_run.user_id,
            source_id=original_run.source_id,
            symbol_id=original_run.symbol_id,
            timeframe=original_run_timeframe(original_run),
            file_name=original_run.file_name,
            parser_source_path=f"correction:{original_run.id}",
            parser_name="human_review_correction",
            parser_version="0.1.0",
            extraction_confidence=Decimal("1.0000"),
            candles=payload.corrected_candles,
            parser_metadata_json={
                "correctedFromChartScreenshotRunId": str(original_run.id),
                "reviewerUserId": (
                    str(payload.reviewer_user_id) if payload.reviewer_user_id is not None else None
                ),
                "reviewNotes": payload.review_notes,
            },
            trigger_analysis=payload.trigger_analysis,
            include_news_correlation=payload.include_news_correlation,
            include_ai_explanation=payload.include_ai_explanation,
            analysis_warmup_start_time=payload.analysis_warmup_start_time,
            analysis_baseline_start_time=payload.analysis_baseline_start_time,
        )
        return await self.create_prediction_run(correction_payload)

    async def trigger_analysis_for_reviewed_run(
        self,
        run: ChartScreenshotRun,
        payload: ChartScreenshotRunReviewRequest,
    ) -> ChartScreenshotRun:
        if run.extracted_window_start is None or run.extracted_window_end is None:
            raise AppError(
                422,
                "chart_screenshot_window_missing",
                "Chart screenshot run has no extracted analysis window",
            )
        try:
            analysis_run = await AnalysisService(self.session).create_historical_run(
                AnalysisRunCreate(
                    workspace_id=run.workspace_id,
                    user_id=payload.reviewer_user_id or run.user_id,
                    symbol_id=run.symbol_id,
                    source_id=run.source_id,
                    timeframe=original_run_timeframe(run),
                    start_time=run.extracted_window_start,
                    end_time=run.extracted_window_end,
                    warmup_start_time=payload.analysis_warmup_start_time,
                    baseline_start_time=payload.analysis_baseline_start_time,
                    include_news_correlation=payload.include_news_correlation,
                    include_ai_explanation=payload.include_ai_explanation,
                )
            )
        except AppError as error:
            await self.session.rollback()
            latest_run = await self.get_run(run.id)
            latest_run.status = ChartScreenshotRunStatus.ANALYSIS_FAILED.value
            latest_run.last_error_code = error.code
            latest_run.last_error_message = error.message
            await self.session.commit()
            await self.session.refresh(latest_run)
            return latest_run
        latest_run = await self.get_run(run.id)
        latest_run.analysis_run_id = analysis_run.id
        latest_run.status = ChartScreenshotRunStatus.ANALYSIS_TRIGGERED.value
        latest_run.parser_metadata_json = {
            **latest_run.parser_metadata_json,
            "analysisTrigger": {
                "analysisRunId": str(analysis_run.id),
                "analysisStatus": str(analysis_run.status),
                "includeNewsCorrelation": payload.include_news_correlation,
                "includeAiExplanation": payload.include_ai_explanation,
                "triggeredByHumanReview": True,
            },
        }
        await self.session.commit()
        await self.session.refresh(latest_run)
        return latest_run

    def with_human_review_metadata(
        self,
        metadata_json: dict[str, object],
        payload: ChartScreenshotRunReviewRequest,
        corrected_run: ChartScreenshotRun | None,
    ) -> dict[str, object]:
        return {
            **metadata_json,
            "humanReview": {
                "status": payload.review_status.value,
                "reviewerUserId": (
                    str(payload.reviewer_user_id) if payload.reviewer_user_id is not None else None
                ),
                "reviewNotes": payload.review_notes,
                "reviewedAt": utc_now().isoformat(),
                "correctedChartScreenshotRunId": (
                    str(corrected_run.id) if corrected_run is not None else None
                ),
                "triggeredAnalysis": payload.trigger_analysis,
                "analysisTarget": (
                    "corrected_run"
                    if corrected_run is not None and payload.trigger_analysis
                    else (
                        "reviewed_run"
                        if payload.review_status == ChartScreenshotReviewStatus.ACCEPTED
                        and payload.trigger_analysis
                        else None
                    )
                ),
            },
        }


def original_run_timeframe(run: ChartScreenshotRun) -> Timeframe:
    return Timeframe(run.timeframe)


def object_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def parse_optional_uuid(value: object) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None
