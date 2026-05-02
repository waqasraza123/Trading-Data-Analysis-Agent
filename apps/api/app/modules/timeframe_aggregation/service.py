from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.repository import AnalysisRepository
from app.modules.candles.models import Candle
from app.modules.candles.repository import CandleRepository
from app.modules.candles.schemas import CandleOriginType, CandleUpsertStatus, NormalizedCandleInput
from app.modules.candles.timeframes import Timeframe, normalize_timestamp, timeframe_duration
from app.modules.candles.validator import validate_candle
from app.modules.data_sources.models import DataSource, DataSourceStatus, DataSourceType
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository
from app.modules.timeframe_aggregation.aggregator import (
    AggregationWindow,
    DerivedCandleCandidate,
    TimeframeAggregator,
    floor_to_boundary,
)
from app.modules.timeframe_aggregation.context import MultiTimeframeContextEngine
from app.modules.timeframe_aggregation.models import (
    CandleAggregationRun,
    CandleAggregationRunStatus,
    DerivedCandleLineage,
    MultiTimeframeContext,
    TimeframeAgreementLabel,
)
from app.modules.timeframe_aggregation.repository import TimeframeAggregationRepository
from app.modules.timeframe_aggregation.schemas import (
    MultiTimeframeContextCreate,
    TimeframeAggregationRunCreate,
)


class TimeframeAggregationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = TimeframeAggregationRepository(session)
        self.candle_repository = CandleRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.signal_repository = SignalRepository(session)
        self.aggregator = TimeframeAggregator()
        self.context_engine = MultiTimeframeContextEngine()

    async def aggregate_timeframe(
        self,
        payload: TimeframeAggregationRunCreate,
    ) -> CandleAggregationRun:
        self.validate_allowed_target(payload.target_timeframe)
        self.aggregator.validate_pair(payload.base_timeframe, payload.target_timeframe)
        normalized_start = normalize_timestamp(payload.start_time)
        normalized_end = normalize_timestamp(payload.end_time)
        await self.validate_symbol_and_source(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
        )
        run = await self.repository.create_run(
            CandleAggregationRun(
                workspace_id=payload.workspace_id,
                symbol_id=payload.symbol_id,
                source_id=payload.source_id,
                base_timeframe=payload.base_timeframe.value,
                target_timeframe=payload.target_timeframe.value,
                start_time=normalized_start,
                end_time=normalized_end,
                status=CandleAggregationRunStatus.RUNNING.value,
                aggregation_version=self.settings.timeframe_aggregation_version,
                summary="Aggregation started",
                metadata_json={},
                started_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        try:
            completed_run = await self.process_aggregation_run(run.id, payload)
            await self.session.commit()
        except AppError:
            await self.session.rollback()
            failed_run = await self.repository.get_run(run.id)
            if failed_run is not None:
                failed_run.status = CandleAggregationRunStatus.FAILED.value
                failed_run.summary = "Aggregation failed before completion"
                failed_run.completed_at = datetime.now(UTC)
                await self.session.commit()
            raise
        except Exception:
            await self.session.rollback()
            failed_run = await self.repository.get_run(run.id)
            if failed_run is not None:
                failed_run.status = CandleAggregationRunStatus.FAILED.value
                failed_run.summary = "Aggregation failed before completion"
                failed_run.completed_at = datetime.now(UTC)
                await self.session.commit()
                return failed_run
            raise
        return completed_run

    async def process_aggregation_run(
        self,
        run_id: UUID,
        payload: TimeframeAggregationRunCreate,
    ) -> CandleAggregationRun:
        run = await self.get_aggregation_run(run_id)
        target_source = await self.get_or_create_derived_data_source(payload.workspace_id)
        symbol = await self.symbol_repository.get_by_id(payload.symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        windows = self.aggregator.build_windows(
            base_timeframe=payload.base_timeframe,
            target_timeframe=payload.target_timeframe,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        base_candles = await self.fetch_base_candles(payload, windows)
        base_candles_by_timestamp = {
            normalize_timestamp(candle.timestamp): candle
            for candle in sorted(base_candles, key=lambda candle: candle.created_at, reverse=True)
        }
        produced_count = 0
        skipped_count = 0
        incomplete_count = 0
        expected_count = 0
        available_count = 0
        incomplete_windows: list[dict[str, object]] = []
        for window in windows:
            expected_count += window.expected_base_count
            actual_base_count = self.actual_base_count(window, base_candles_by_timestamp)
            available_count += actual_base_count
            candidate = self.aggregator.aggregate_window(window, list(base_candles_by_timestamp.values()))
            if candidate is None:
                incomplete_count += 1
                skipped_count += 1
                incomplete_windows.append(
                    self.incomplete_window_metadata(window, actual_base_count)
                )
                continue
            if candidate.completeness_score < self.settings.timeframe_aggregation_min_completeness:
                incomplete_count += 1
                skipped_count += 1
                incomplete_windows.append(
                    self.incomplete_window_metadata(window, candidate.actual_base_count)
                )
                continue
            stored = await self.store_derived_candle(
                payload=payload,
                run=run,
                target_source=target_source,
                candidate=candidate,
                symbol=symbol,
            )
            if stored is None:
                skipped_count += 1
                continue
            produced_count += 1
        run.expected_base_candle_count = expected_count
        run.available_base_candle_count = available_count
        run.produced_candle_count = produced_count
        run.skipped_candle_count = skipped_count
        run.incomplete_window_count = incomplete_count
        run.status = (
            CandleAggregationRunStatus.COMPLETED_WITH_WARNINGS.value
            if incomplete_count or skipped_count
            else CandleAggregationRunStatus.COMPLETED.value
        )
        run.summary = self.aggregation_summary(produced_count, incomplete_count, skipped_count)
        run.metadata_json = {
            "derivedSourceId": str(target_source.id),
            "windowCount": len(windows),
            "incompleteWindows": incomplete_windows[:100],
            "incompleteWindowOverflow": max(len(incomplete_windows) - 100, 0),
        }
        run.completed_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def store_derived_candle(
        self,
        payload: TimeframeAggregationRunCreate,
        run: CandleAggregationRun,
        target_source: DataSource,
        candidate: DerivedCandleCandidate,
        symbol: Symbol,
    ) -> UUID | None:
        normalized = NormalizedCandleInput(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=target_source.id,
            timeframe=payload.target_timeframe,
            timestamp=candidate.window.derived_timestamp,
            open=candidate.open,
            high=candidate.high,
            low=candidate.low,
            close=candidate.close,
            volume=candidate.volume,
            is_final=True,
            origin_type=CandleOriginType.DERIVED_AGGREGATION,
            origin_reference_id=run.id,
        )
        validation = validate_candle(normalized, symbol, target_source)
        if not validation.is_valid:
            raise AppError(422, "invalid_derived_candle", "Derived candle validation failed")
        result = await self.candle_repository.upsert_normalized_candle(normalized)
        if result.status == CandleUpsertStatus.CONFLICTING_FINAL or result.candle_id is None:
            return None
        await self.repository.create_lineage(
            DerivedCandleLineage(
                workspace_id=payload.workspace_id,
                aggregation_run_id=run.id,
                derived_candle_id=result.candle_id,
                symbol_id=payload.symbol_id,
                source_id=payload.source_id,
                base_timeframe=payload.base_timeframe.value,
                target_timeframe=payload.target_timeframe.value,
                derived_timestamp=candidate.window.derived_timestamp,
                base_start_time=candidate.window.base_start_time,
                base_end_time=candidate.window.base_end_time,
                expected_base_count=candidate.window.expected_base_count,
                actual_base_count=candidate.actual_base_count,
                completeness_score=candidate.completeness_score,
                is_complete=True,
                metadata_json={
                    "aggregationVersion": self.settings.timeframe_aggregation_version,
                    "derivedSourceId": str(target_source.id),
                },
            )
        )
        return result.candle_id

    async def get_aggregation_run(self, run_id: UUID) -> CandleAggregationRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "aggregation_run_not_found", "Aggregation run not found")
        return run

    async def list_aggregation_runs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        symbol_id: UUID | None = None,
        status: str | None = None,
        base_timeframe: str | None = None,
        target_timeframe: str | None = None,
    ) -> list[CandleAggregationRun]:
        return await self.repository.list_runs(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            status=status,
            base_timeframe=base_timeframe,
            target_timeframe=target_timeframe,
        )

    async def get_derived_lineage(self, derived_candle_id: UUID) -> list[DerivedCandleLineage]:
        lineage = await self.repository.get_lineage_by_derived_candle_id(derived_candle_id)
        if not lineage:
            raise AppError(404, "derived_candle_lineage_not_found", "Derived candle lineage not found")
        return lineage

    async def build_context_for_analysis_run(
        self,
        analysis_run_id: UUID,
        context_timeframes: list[Timeframe],
        force_recompute: bool = False,
    ) -> MultiTimeframeContext:
        existing = await self.repository.get_context_for_analysis_run(analysis_run_id)
        if existing is not None and not force_recompute:
            return existing
        if force_recompute:
            await self.repository.delete_context_for_analysis_run(analysis_run_id)
        analysis_run = await self.analysis_repository.get_run(analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        signal = await self.signal_repository.get_by_analysis_run_id(analysis_run_id)
        return await self.create_context(
            analysis_run_id=analysis_run.id,
            signal=signal,
            workspace_id=analysis_run.workspace_id,
            symbol_id=analysis_run.symbol_id,
            source_id=analysis_run.source_id,
            primary_timeframe=Timeframe(analysis_run.timeframe),
            context_timeframes=context_timeframes,
            end_time=analysis_run.end_time,
        )

    async def build_context_for_signal(
        self,
        signal_id: UUID,
        context_timeframes: list[Timeframe],
        force_recompute: bool = False,
    ) -> MultiTimeframeContext:
        existing = await self.repository.get_context_for_signal(signal_id)
        if existing is not None and not force_recompute:
            return existing
        if force_recompute:
            await self.repository.delete_context_for_signal(signal_id)
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        analysis_run = await self.analysis_repository.get_run(signal.analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return await self.create_context(
            analysis_run_id=analysis_run.id,
            signal=signal,
            workspace_id=signal.workspace_id,
            symbol_id=signal.symbol_id,
            source_id=analysis_run.source_id,
            primary_timeframe=Timeframe(signal.timeframe),
            context_timeframes=context_timeframes,
            end_time=analysis_run.end_time,
        )

    async def create_context(
        self,
        analysis_run_id: UUID | None,
        signal: Signal | None,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
        primary_timeframe: Timeframe,
        context_timeframes: list[Timeframe],
        end_time: datetime,
    ) -> MultiTimeframeContext:
        resolved_timeframes = self.resolve_context_timeframes(primary_timeframe, context_timeframes)
        snapshots = []
        for timeframe in resolved_timeframes:
            candles = await self.fetch_context_candles(
                workspace_id=workspace_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                end_time=end_time,
                source_id=source_id,
            )
            if not candles and source_id is not None:
                candles = await self.fetch_context_candles(
                    workspace_id=workspace_id,
                    symbol_id=symbol_id,
                    timeframe=timeframe,
                    end_time=end_time,
                    source_id=None,
                )
            snapshots.append(self.context_engine.snapshot_from_candles(timeframe.value, candles))
        result = self.context_engine.build(signal, snapshots)
        context = await self.repository.create_context(
            MultiTimeframeContext(
                workspace_id=workspace_id,
                analysis_run_id=analysis_run_id,
                signal_id=signal.id if signal is not None else None,
                symbol_id=symbol_id,
                source_id=source_id,
                primary_timeframe=primary_timeframe.value,
                context_timeframes_json=[timeframe.value for timeframe in resolved_timeframes],
                context_version=self.settings.multi_timeframe_context_version,
                trend_alignment=result.trend_alignment.value,
                volatility_alignment=result.volatility_alignment.value,
                range_alignment=result.range_alignment.value,
                agreement_score=result.agreement_score,
                agreement_label=result.agreement_label.value,
                context_summary=result.context_summary,
                context_json=result.context_json,
                warnings_json=result.warnings_json,
            )
        )
        await self.session.commit()
        return context

    async def get_context_for_analysis_run(self, analysis_run_id: UUID) -> MultiTimeframeContext:
        context = await self.repository.get_context_for_analysis_run(analysis_run_id)
        if context is None:
            raise AppError(404, "multi_timeframe_context_not_found", "Multi-timeframe context not found")
        return context

    async def get_context_for_signal(self, signal_id: UUID) -> MultiTimeframeContext:
        context = await self.repository.get_context_for_signal(signal_id)
        if context is None:
            raise AppError(404, "multi_timeframe_context_not_found", "Multi-timeframe context not found")
        return context

    async def fetch_base_candles(
        self,
        payload: TimeframeAggregationRunCreate,
        windows: list[AggregationWindow],
    ) -> list[Candle]:
        if not windows:
            return []
        return await self.repository.list_final_candles(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            timeframe=payload.base_timeframe.value,
            start_time=windows[0].base_start_time,
            end_time=windows[-1].base_end_time,
            source_id=payload.source_id,
        )

    async def fetch_context_candles(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        end_time: datetime,
        source_id: UUID | None,
    ) -> list[Candle]:
        normalized_end = floor_to_boundary(normalize_timestamp(end_time), timeframe_duration(timeframe))
        return await self.repository.list_recent_final_candles(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe.value,
            end_time=normalized_end,
            source_id=source_id,
            limit=30,
        )

    async def validate_symbol_and_source(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
    ) -> None:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if source_id is None:
            return
        source = await self.data_source_repository.get_by_id(source_id)
        if source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if source.workspace_id != workspace_id:
            raise AppError(422, "workspace_source_mismatch", "Data source does not belong to workspace")

    async def get_or_create_derived_data_source(self, workspace_id: UUID) -> DataSource:
        name = "Derived candle aggregation"
        provider = "internal_timeframe_aggregation"
        source_type = DataSourceType.DERIVED_AGGREGATION.value
        existing = await self.data_source_repository.get_by_natural_key(
            workspace_id=workspace_id,
            name=name,
            provider=provider,
            source_type=source_type,
        )
        if existing is not None:
            return existing
        return await self.data_source_repository.create(
            DataSource(
                workspace_id=workspace_id,
                name=name,
                provider=provider,
                source_type=source_type,
                status=DataSourceStatus.ACTIVE.value,
                config_json={
                    "sourcePolicy": "derived_candles_only",
                    "aggregationVersion": self.settings.timeframe_aggregation_version,
                },
            )
        )

    def resolve_context_timeframes(
        self,
        primary_timeframe: Timeframe,
        requested_timeframes: list[Timeframe],
    ) -> list[Timeframe]:
        source = requested_timeframes or [
            Timeframe(value)
            for value in self.settings.timeframe_aggregation_allowed_targets
            if value in Timeframe._value2member_map_
        ]
        primary_duration = timeframe_duration(primary_timeframe)
        result = [
            timeframe
            for timeframe in source
            if timeframe_duration(timeframe) > primary_duration
            and timeframe.value in self.settings.timeframe_aggregation_allowed_targets
        ]
        if not result:
            raise AppError(
                422,
                "invalid_context_timeframes",
                "At least one higher allowed context timeframe is required",
            )
        return result

    def validate_allowed_target(self, target_timeframe: Timeframe) -> None:
        if target_timeframe.value not in self.settings.timeframe_aggregation_allowed_targets:
            raise AppError(422, "target_timeframe_not_allowed", "Target timeframe is not allowed")

    def actual_base_count(
        self,
        window: AggregationWindow,
        candles_by_timestamp: dict[datetime, Candle],
    ) -> int:
        count = 0
        current = window.base_start_time
        step = (window.base_end_time - window.base_start_time) / max(window.expected_base_count - 1, 1)
        if window.expected_base_count == 1:
            return 1 if current in candles_by_timestamp else 0
        while current <= window.base_end_time:
            if current in candles_by_timestamp:
                count += 1
            current += step
        return count

    def incomplete_window_metadata(
        self,
        window: AggregationWindow,
        actual_base_count: int,
    ) -> dict[str, object]:
        return {
            "derivedTimestamp": window.derived_timestamp.isoformat(),
            "baseStartTime": window.base_start_time.isoformat(),
            "baseEndTime": window.base_end_time.isoformat(),
            "expectedBaseCount": window.expected_base_count,
            "actualBaseCount": actual_base_count,
            "completenessScore": str(
                self.aggregator.completeness_score(window.expected_base_count, actual_base_count)
            ),
        }

    def aggregation_summary(
        self,
        produced_count: int,
        incomplete_count: int,
        skipped_count: int,
    ) -> str:
        if incomplete_count or skipped_count:
            return (
                f"Produced {produced_count} complete derived candles; "
                f"skipped {skipped_count} windows with {incomplete_count} incomplete windows."
            )
        return f"Produced {produced_count} complete derived candles."


def context_payload_or_default(payload: MultiTimeframeContextCreate | None) -> MultiTimeframeContextCreate:
    return payload or MultiTimeframeContextCreate()
