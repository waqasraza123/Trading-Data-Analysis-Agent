from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.analysis.schemas import AnalysisRunCreate
from app.modules.analysis.service import AnalysisService
from app.modules.candles.normalizer import RawCandlePayload, normalize_candle_payload
from app.modules.candles.repository import CandleRepository
from app.modules.candles.schemas import CandleOriginType, CandleUpsertStatus
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
from app.modules.chart_screenshots.schemas import ChartScreenshotPredictionCreate
from app.modules.data_sources.models import DataSource, DataSourceType
from app.modules.data_sources.repository import DataSourceRepository
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
                        "candles": [
                            candle.model_dump(mode="json") for candle in payload.candles
                        ],
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
            [str(item) for item in raw_warning_items]
            if isinstance(raw_warning_items, list)
            else []
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
