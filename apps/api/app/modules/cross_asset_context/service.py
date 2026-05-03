from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.analysis.repository import AnalysisRepository
from app.modules.candles.models import Candle
from app.modules.cross_asset_context.calculator import (
    CrossAssetCalculationInput,
    CrossAssetCandleSnapshot,
    CrossAssetContextCalculator,
)
from app.modules.cross_asset_context.models import (
    CrossAssetAlignmentLabel,
    CrossAssetContextResult,
    CrossAssetContextRun,
    CrossAssetContextRunStatus,
)
from app.modules.cross_asset_context.repository import CrossAssetContextRepository
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository


class CrossAssetContextService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = CrossAssetContextRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.signal_repository = SignalRepository(session)
        self.calculator = CrossAssetContextCalculator()

    async def build_for_analysis_run(
        self,
        analysis_run_id: UUID,
        compared_symbol_ids: list[UUID],
        force_recompute: bool = False,
    ) -> CrossAssetContextRun:
        analysis_run = await self.get_analysis_run(analysis_run_id)
        existing = await self.repository.get_latest_for_analysis_run(
            analysis_run_id,
            self.context_version,
        )
        resolved_symbol_ids = await self.validate_compared_symbols(
            base_symbol_id=analysis_run.symbol_id,
            compared_symbol_ids=compared_symbol_ids,
        )
        if (
            existing is not None
            and not force_recompute
            and run_matches_symbols(existing, resolved_symbol_ids)
        ):
            return existing
        if force_recompute:
            await self.repository.delete_for_analysis_run(analysis_run_id, self.context_version)
        signal = await self.signal_repository.get_by_analysis_run_id(analysis_run_id)
        return await self.create_context_run(
            analysis_run=analysis_run,
            signal=signal,
            compared_symbol_ids=resolved_symbol_ids,
            source="analysis_run",
        )

    async def build_for_signal(
        self,
        signal_id: UUID,
        compared_symbol_ids: list[UUID],
        force_recompute: bool = False,
    ) -> CrossAssetContextRun:
        signal = await self.get_signal(signal_id)
        analysis_run = await self.get_analysis_run(signal.analysis_run_id)
        existing = await self.repository.get_latest_for_signal(signal_id, self.context_version)
        resolved_symbol_ids = await self.validate_compared_symbols(
            base_symbol_id=signal.symbol_id,
            compared_symbol_ids=compared_symbol_ids,
        )
        if (
            existing is not None
            and not force_recompute
            and run_matches_symbols(existing, resolved_symbol_ids)
        ):
            return existing
        if force_recompute:
            await self.repository.delete_for_signal(signal_id, self.context_version)
        return await self.create_context_run(
            analysis_run=analysis_run,
            signal=signal,
            compared_symbol_ids=resolved_symbol_ids,
            source="signal",
        )

    async def get_for_analysis_run(self, analysis_run_id: UUID) -> CrossAssetContextRun:
        await self.get_analysis_run(analysis_run_id)
        run = await self.repository.get_latest_for_analysis_run(
            analysis_run_id,
            self.context_version,
        )
        if run is None:
            raise AppError(404, "cross_asset_context_not_found", "Cross-asset context not found")
        return run

    async def get_for_signal(self, signal_id: UUID) -> CrossAssetContextRun:
        await self.get_signal(signal_id)
        run = await self.repository.get_latest_for_signal(signal_id, self.context_version)
        if run is None:
            raise AppError(404, "cross_asset_context_not_found", "Cross-asset context not found")
        return run

    async def list_results(
        self,
        context_run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[CrossAssetContextResult]:
        run = await self.repository.get_run(context_run_id)
        if run is None:
            raise AppError(
                404,
                "cross_asset_context_run_not_found",
                "Cross-asset context run not found",
            )
        return await self.repository.list_results(context_run_id, limit, offset)

    async def create_context_run(
        self,
        analysis_run: AnalysisRun,
        signal: Signal | None,
        compared_symbol_ids: list[UUID],
        source: str,
    ) -> CrossAssetContextRun:
        await self.add_audit_log(
            analysis_run.id,
            "cross_asset_context_started",
            "Cross-asset context calculation started",
            {
                "comparedSymbolIds": [str(symbol_id) for symbol_id in compared_symbol_ids],
                "contextVersion": self.context_version,
                "source": source,
            },
        )
        try:
            run = await self.repository.create_run(
                CrossAssetContextRun(
                    workspace_id=analysis_run.workspace_id,
                    analysis_run_id=analysis_run.id,
                    signal_id=signal.id if signal is not None else None,
                    base_symbol_id=analysis_run.symbol_id,
                    timeframe=analysis_run.timeframe,
                    source_id=analysis_run.source_id,
                    context_version=self.context_version,
                    status=CrossAssetContextRunStatus.PENDING.value,
                    start_time=normalize_datetime(analysis_run.start_time),
                    end_time=normalize_datetime(analysis_run.end_time),
                    compared_symbol_count=len(compared_symbol_ids),
                    result_count=0,
                    summary="Cross-asset context calculation pending",
                    metadata_json={
                        "requestedComparedSymbolIds": [
                            str(symbol_id) for symbol_id in compared_symbol_ids
                        ],
                        "source": source,
                    },
                )
            )
            results = await self.calculate_results(run, compared_symbol_ids)
            persisted_results = await self.repository.create_results(results)
            run.result_count = len(persisted_results)
            run.status = status_for_results(persisted_results)
            run.summary = summary_for_results(persisted_results)
            run.metadata_json = {
                **run.metadata_json,
                "completedAt": datetime.now(UTC).isoformat(),
                "settings": {
                    "minimumCandles": self.settings.cross_asset_min_candles,
                    "leadLagMaxOffset": self.settings.cross_asset_lead_lag_max_offset,
                    "alignmentThreshold": str(self.settings.cross_asset_alignment_threshold),
                    "divergenceThreshold": str(self.settings.cross_asset_divergence_threshold),
                },
                "languagePolicy": {
                    "contextOnly": True,
                    "noCausation": True,
                    "noFinancialAdvice": True,
                    "noSignalMutation": True,
                },
            }
            await self.add_audit_log(
                analysis_run.id,
                "cross_asset_context_completed",
                "Cross-asset context calculation completed",
                {
                    "crossAssetContextRunId": str(run.id),
                    "resultCount": run.result_count,
                    "status": run.status,
                },
            )
            await self.session.commit()
            await self.session.refresh(run)
            return run
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "cross_asset_context_conflict",
                "Cross-asset context could not be persisted",
            ) from error
        except AppError:
            await self.session.rollback()
            raise
        except Exception as error:
            await self.session.rollback()
            raise AppError(
                500,
                "cross_asset_context_failed",
                "Cross-asset context calculation failed",
            ) from error

    async def calculate_results(
        self,
        run: CrossAssetContextRun,
        compared_symbol_ids: list[UUID],
    ) -> list[CrossAssetContextResult]:
        base_candles = await self.fetch_context_candles(
            workspace_id=run.workspace_id,
            symbol_id=run.base_symbol_id,
            timeframe=run.timeframe,
            start_time=run.start_time,
            end_time=run.end_time,
            source_id=run.source_id,
        )
        results: list[CrossAssetContextResult] = []
        for compared_symbol_id in compared_symbol_ids:
            compared_candles = await self.fetch_context_candles(
                workspace_id=run.workspace_id,
                symbol_id=compared_symbol_id,
                timeframe=run.timeframe,
                start_time=run.start_time,
                end_time=run.end_time,
                source_id=run.source_id,
            )
            calculation = self.calculator.calculate(
                CrossAssetCalculationInput(
                    base_symbol_id=run.base_symbol_id,
                    compared_symbol_id=compared_symbol_id,
                    timeframe=run.timeframe,
                    start_time=run.start_time,
                    end_time=run.end_time,
                    base_candles=candle_snapshots(base_candles),
                    compared_candles=candle_snapshots(compared_candles),
                    min_candles=self.settings.cross_asset_min_candles,
                    lead_lag_max_offset=self.settings.cross_asset_lead_lag_max_offset,
                    alignment_threshold=self.settings.cross_asset_alignment_threshold,
                    divergence_threshold=self.settings.cross_asset_divergence_threshold,
                )
            )
            results.append(
                CrossAssetContextResult(
                    workspace_id=run.workspace_id,
                    context_run_id=run.id,
                    base_symbol_id=run.base_symbol_id,
                    compared_symbol_id=compared_symbol_id,
                    timeframe=run.timeframe,
                    start_time=run.start_time,
                    end_time=run.end_time,
                    base_move=calculation.base_move,
                    compared_move=calculation.compared_move,
                    base_direction=calculation.base_direction,
                    compared_direction=calculation.compared_direction,
                    correlation_score=calculation.correlation_score,
                    alignment_label=calculation.alignment_label.value,
                    lead_lag_offset_candles=calculation.lead_lag_offset_candles,
                    lead_lag_label=calculation.lead_lag_label.value,
                    divergence_score=calculation.divergence_score,
                    data_quality_label=calculation.data_quality_label.value,
                    metadata_json=calculation.metadata_json,
                )
            )
        return results

    async def fetch_context_candles(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        source_id: UUID | None,
    ) -> list[Candle]:
        candles = await self.repository.list_final_candles(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            source_id=source_id,
        )
        if candles or source_id is None:
            return candles
        return await self.repository.list_final_candles(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            source_id=None,
        )

    async def validate_compared_symbols(
        self,
        base_symbol_id: UUID,
        compared_symbol_ids: list[UUID],
    ) -> list[UUID]:
        if len(compared_symbol_ids) > self.settings.cross_asset_max_compared_symbols:
            raise AppError(
                422,
                "too_many_compared_symbols",
                "Too many compared symbols requested",
            )
        if base_symbol_id in compared_symbol_ids:
            raise AppError(
                422,
                "compared_symbol_matches_base",
                "Compared symbols must not include the base symbol",
            )
        symbols = await self.repository.list_symbols_by_ids(compared_symbol_ids)
        found_ids = {symbol.id for symbol in symbols}
        if len(found_ids) != len(compared_symbol_ids):
            raise AppError(404, "symbol_not_found", "One or more compared symbols were not found")
        ordered_symbols = sorted(symbols, key=lambda symbol: compared_symbol_ids.index(symbol.id))
        return [symbol.id for symbol in ordered_symbols]

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return run

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
    def context_version(self) -> str:
        return self.settings.cross_asset_context_version


def candle_snapshots(candles: list[Candle]) -> list[CrossAssetCandleSnapshot]:
    return [
        CrossAssetCandleSnapshot(timestamp=candle.timestamp, open=candle.open, close=candle.close)
        for candle in candles
    ]


def status_for_results(results: list[CrossAssetContextResult]) -> str:
    if not results:
        return CrossAssetContextRunStatus.COMPLETED_WITH_WARNINGS.value
    if any(
        result.alignment_label == CrossAssetAlignmentLabel.INSUFFICIENT_DATA.value
        for result in results
    ):
        return CrossAssetContextRunStatus.COMPLETED_WITH_WARNINGS.value
    return CrossAssetContextRunStatus.COMPLETED.value


def summary_for_results(results: list[CrossAssetContextResult]) -> str:
    if not results:
        return "Cross-asset context completed with no compared symbols."
    alignment_counts = Counter(result.alignment_label for result in results)
    lead_lag_counts = Counter(result.lead_lag_label for result in results)
    return (
        "Cross-asset context completed: "
        f"{alignment_counts.get('aligned', 0)} aligned, "
        f"{alignment_counts.get('partially_aligned', 0)} partially aligned, "
        f"{alignment_counts.get('conflicting', 0)} conflicting, "
        f"{alignment_counts.get('divergent', 0)} divergent, "
        f"{alignment_counts.get('insufficient_data', 0)} insufficient data; "
        f"{lead_lag_counts.get('base_leads', 0)} base leads, "
        f"{lead_lag_counts.get('compared_leads', 0)} compared leads."
    )


def run_matches_symbols(run: CrossAssetContextRun, compared_symbol_ids: list[UUID]) -> bool:
    existing = run.metadata_json.get("requestedComparedSymbolIds", [])
    return existing == [str(symbol_id) for symbol_id in compared_symbol_ids]


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
