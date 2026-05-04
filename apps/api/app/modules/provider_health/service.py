from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.candle_gap_recovery.schemas import (
    CandleGapRecoveryPlanCreate,
    PrepareProviderPollingResponse,
)
from app.modules.candle_gap_recovery.service import CandleGapRecoveryService
from app.modules.candles.quality import (
    CandleQualityInput,
    CandleQualityReport,
    calculate_candle_quality,
)
from app.modules.candles.timeframes import Timeframe, timeframe_duration
from app.modules.data_quality.models import DataQualityLabel
from app.modules.data_sources.models import DataSource, DataSourceStatus
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.live.models import LiveFeedSubscriptionStatus
from app.modules.provider_health.models import (
    ProviderHealthFreshnessLabel,
    ProviderHealthSnapshot,
    ProviderHealthStatus,
)
from app.modules.provider_health.repository import ProviderHealthRepository
from app.modules.provider_health.schemas import (
    ProviderHealthPrepareGapRecoveryResponse,
    ProviderHealthSnapshotListFilters,
    ProviderHealthSnapshotRead,
    ProviderHealthSummary,
)
from app.modules.provider_polling.models import ProviderPollingRequest, ProviderPollingRequestStatus
from app.modules.symbols.repository import SymbolRepository


@dataclass(frozen=True)
class HealthWindow:
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class SnapshotInputs:
    data_source: DataSource
    latest_final_candle_time: datetime | None
    latest_successful_poll_at: datetime | None
    latest_failed_poll_at: datetime | None
    latest_gap_recovery_plan_id: UUID | None
    latest_data_quality_run_id: UUID | None
    consecutive_failure_count: int
    missing_candle_count: int
    freshness_label: ProviderHealthFreshnessLabel
    stale_seconds: int | None
    summary: str
    metadata_json: dict[str, object]


class ProviderHealthService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ProviderHealthRepository(session)
        self.data_source_repository = DataSourceRepository(session)
        self.symbol_repository = SymbolRepository(session)

    async def build_health_snapshot(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        force_recompute: bool = False,
    ) -> ProviderHealthSnapshot:
        await self.validate_identity(workspace_id, source_id, symbol_id, timeframe)
        existing = await self.repository.get_latest_snapshot(
            workspace_id=workspace_id,
            source_id=source_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
        )
        if existing is not None and not force_recompute and snapshot_is_current(existing):
            return existing
        inputs = await self.build_snapshot_inputs(
            workspace_id=workspace_id,
            source_id=source_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
        )
        snapshot = ProviderHealthSnapshot(
            workspace_id=workspace_id,
            source_id=source_id,
            provider=inputs.data_source.provider,
            symbol_id=symbol_id,
            timeframe=timeframe,
            status=self.determine_status(inputs).value,
            freshness_label=inputs.freshness_label.value,
            latest_final_candle_time=inputs.latest_final_candle_time,
            latest_successful_poll_at=inputs.latest_successful_poll_at,
            latest_failed_poll_at=inputs.latest_failed_poll_at,
            latest_gap_recovery_plan_id=inputs.latest_gap_recovery_plan_id,
            latest_data_quality_run_id=inputs.latest_data_quality_run_id,
            consecutive_failure_count=inputs.consecutive_failure_count,
            missing_candle_count=inputs.missing_candle_count,
            stale_seconds=inputs.stale_seconds,
            summary=inputs.summary,
            metadata_json=inputs.metadata_json,
        )
        try:
            created = await self.repository.create_snapshot(snapshot)
            await self.session.commit()
            await self.session.refresh(created)
            return created
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "provider_health_snapshot_conflict",
                "Provider health snapshot could not be persisted",
            ) from error

    async def get_health_snapshot(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
    ) -> ProviderHealthSnapshot:
        await self.validate_identity(workspace_id, source_id, symbol_id, timeframe)
        snapshot = await self.repository.get_latest_snapshot(
            workspace_id=workspace_id,
            source_id=source_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
        )
        if snapshot is None:
            raise AppError(
                404,
                "provider_health_snapshot_not_found",
                "Provider health snapshot not found",
            )
        return snapshot

    async def list_health_snapshots(
        self,
        filters: ProviderHealthSnapshotListFilters,
    ) -> list[ProviderHealthSnapshot]:
        return await self.repository.list_snapshots(
            workspace_id=filters.workspace_id,
            source_id=filters.source_id,
            symbol_id=filters.symbol_id,
            timeframe=filters.timeframe.value if filters.timeframe is not None else None,
            provider=filters.provider,
            status=filters.status.value if filters.status is not None else None,
            freshness_label=(
                filters.freshness_label.value if filters.freshness_label is not None else None
            ),
            limit=filters.limit,
            offset=filters.offset,
        )

    async def build_workspace_health(
        self,
        workspace_id: UUID,
        limit: int = 500,
    ) -> tuple[list[ProviderHealthSnapshot], int]:
        candidates = await self.repository.list_refresh_candidates(workspace_id, limit)
        snapshots: list[ProviderHealthSnapshot] = []
        skipped_count = 0
        for candidate in candidates:
            try:
                snapshot = await self.build_health_snapshot(
                    workspace_id=candidate.workspace_id,
                    source_id=candidate.source_id,
                    symbol_id=candidate.symbol_id,
                    timeframe=candidate.timeframe,
                    force_recompute=True,
                )
            except AppError:
                skipped_count += 1
                continue
            snapshots.append(snapshot)
        return snapshots, skipped_count

    async def summarize_provider_health(self, workspace_id: UUID) -> ProviderHealthSummary:
        summary_payload = await self.repository.summarize_workspace(workspace_id)
        snapshots = summary_payload["snapshots"]
        if not isinstance(snapshots, list):
            snapshots = []
        return ProviderHealthSummary(
            workspace_id=workspace_id,
            total_snapshots=len(snapshots),
            healthy_count=count_status(snapshots, ProviderHealthStatus.HEALTHY),
            degraded_count=count_status(snapshots, ProviderHealthStatus.DEGRADED),
            stale_count=count_status(snapshots, ProviderHealthStatus.STALE),
            failing_count=count_status(snapshots, ProviderHealthStatus.FAILING),
            unavailable_count=count_status(snapshots, ProviderHealthStatus.UNAVAILABLE),
            unknown_count=count_status(snapshots, ProviderHealthStatus.UNKNOWN),
            fresh_count=count_freshness(snapshots, ProviderHealthFreshnessLabel.FRESH),
            delayed_count=count_freshness(snapshots, ProviderHealthFreshnessLabel.DELAYED),
            no_data_count=count_freshness(snapshots, ProviderHealthFreshnessLabel.NO_DATA),
            missing_candle_count=sum(snapshot.missing_candle_count for snapshot in snapshots),
            provider_failure_count=sum(
                snapshot.consecutive_failure_count for snapshot in snapshots
            ),
            ready_for_deterministic_analysis_count=sum(
                1
                for snapshot in snapshots
                if snapshot.symbol_id is not None
                and snapshot.timeframe is not None
                and snapshot.status == ProviderHealthStatus.HEALTHY.value
                and snapshot.freshness_label
                in {
                    ProviderHealthFreshnessLabel.FRESH.value,
                    ProviderHealthFreshnessLabel.DELAYED.value,
                }
                and snapshot.missing_candle_count == 0
            ),
            latest_snapshot_at=summary_payload.get("latestSnapshotAt"),
        )

    async def prepare_gap_recovery(
        self,
        snapshot_id: UUID,
        create_requests: bool,
    ) -> ProviderHealthPrepareGapRecoveryResponse:
        snapshot = await self.repository.get_snapshot(snapshot_id)
        if snapshot is None:
            raise AppError(
                404,
                "provider_health_snapshot_not_found",
                "Provider health snapshot not found",
            )
        if snapshot.symbol_id is None or snapshot.timeframe is None:
            raise AppError(
                422,
                "provider_health_snapshot_not_symbol_scoped",
                "Gap recovery preparation requires a symbol and timeframe snapshot",
            )
        gap_service = CandleGapRecoveryService(self.session, self.settings)
        created_plan = False
        plan = None
        if snapshot.latest_gap_recovery_plan_id is not None:
            plan = await gap_service.get_recovery_plan(snapshot.latest_gap_recovery_plan_id)
        if plan is None:
            window = self.gap_recovery_window(snapshot)
            plan = await gap_service.create_recovery_plan(
                CandleGapRecoveryPlanCreate(
                    workspace_id=snapshot.workspace_id,
                    source_id=snapshot.source_id,
                    symbol_id=snapshot.symbol_id,
                    timeframe=Timeframe(snapshot.timeframe),
                    start_time=window.start_time,
                    end_time=window.end_time,
                )
            )
            snapshot.latest_gap_recovery_plan_id = plan.id
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(snapshot)
            created_plan = True
        preparation: PrepareProviderPollingResponse | None = None
        if plan.detected_gap_count > 0:
            preparation = await gap_service.prepare_provider_polling_requests(
                plan.id,
                create_requests=create_requests,
            )
        return ProviderHealthPrepareGapRecoveryResponse(
            snapshot=ProviderHealthSnapshotRead.model_validate(snapshot),
            recovery_plan=gap_service_plan_read(plan),
            preparation=preparation,
            created_plan=created_plan,
        )

    async def build_snapshot_inputs(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None,
        timeframe: str | None,
    ) -> SnapshotInputs:
        data_source = await self.load_data_source(workspace_id, source_id)
        latest_final_candle = None
        quality_report = None
        window = None
        if symbol_id is not None and timeframe is not None:
            latest_final_candle = await self.repository.get_latest_final_candle(
                workspace_id=workspace_id,
                source_id=source_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
            )
            window = self.health_window(
                timeframe,
                latest_final_candle.timestamp if latest_final_candle else None,
            )
            quality_report = await self.calculate_quality_report(
                workspace_id=workspace_id,
                source_id=source_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                window=window,
            )
        recent_polling_requests = await self.repository.list_recent_polling_requests(
            workspace_id=workspace_id,
            source_id=source_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            limit=10,
        )
        latest_successful_poll = await self.repository.get_latest_successful_poll(
            workspace_id,
            source_id,
            symbol_id,
            timeframe,
        )
        latest_failed_poll = await self.repository.get_latest_failed_poll(
            workspace_id,
            source_id,
            symbol_id,
            timeframe,
        )
        recent_errors = await self.repository.list_recent_polling_errors(
            workspace_id=workspace_id,
            source_id=source_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            limit=5,
        )
        latest_gap_plan = (
            await self.repository.get_latest_gap_recovery_plan(
                workspace_id,
                source_id,
                symbol_id,
                timeframe,
            )
            if symbol_id is not None and timeframe is not None
            else None
        )
        latest_data_quality_run = (
            await self.repository.get_latest_data_quality_run(
                workspace_id,
                source_id,
                symbol_id,
                timeframe,
            )
            if symbol_id is not None and timeframe is not None
            else None
        )
        live_subscription = await self.repository.get_latest_live_subscription(
            workspace_id,
            source_id,
            symbol_id,
            timeframe,
        )
        market_memory = (
            await self.repository.get_latest_market_memory(
                workspace_id,
                source_id,
                symbol_id,
                timeframe,
            )
            if symbol_id is not None and timeframe is not None
            else None
        )
        freshness_label = self.determine_freshness_label(
            latest_final_candle.timestamp if latest_final_candle is not None else None,
            timeframe,
        )
        stale_seconds = self.calculate_stale_seconds(
            latest_final_candle.timestamp if latest_final_candle is not None else None
        )
        consecutive_failure_count = count_consecutive_failures(recent_polling_requests)
        missing_candle_count = quality_report.missing_candles if quality_report is not None else 0
        metadata_json = {
            "providerHealthVersion": self.settings.provider_health_version,
            "source": {
                "name": data_source.name,
                "sourceType": data_source.source_type,
                "status": data_source.status,
            },
            "qualityWindow": (
                {
                    "startTime": window.start_time.isoformat(),
                    "endTime": window.end_time.isoformat(),
                    "expectedCandles": quality_report.expected_candles,
                    "availableFinalCandles": quality_report.available_final_candles,
                    "availablePartialCandles": quality_report.available_partial_candles,
                    "duplicateCandles": quality_report.duplicate_candles,
                    "qualityScore": str(quality_report.quality_score),
                }
                if quality_report is not None and window is not None
                else None
            ),
            "latestProviderPollingRequest": compact_polling_request(
                recent_polling_requests[0] if recent_polling_requests else None
            ),
            "recentProviderFailures": [
                {
                    "errorCode": error.error_code,
                    "errorMessage": error.error_message,
                    "createdAt": error.created_at.isoformat(),
                }
                for error in recent_errors
            ],
            "latestLiveSubscription": (
                {
                    "id": str(live_subscription.id),
                    "status": live_subscription.status,
                    "lastMessageAt": iso_or_none(live_subscription.last_message_at),
                    "lastFinalCandleAt": iso_or_none(live_subscription.last_final_candle_at),
                    "lastError": live_subscription.last_error,
                }
                if live_subscription is not None
                else None
            ),
            "marketMemory": (
                {
                    "id": str(market_memory.id),
                    "freshnessLabel": market_memory.freshness_label,
                    "dataQualityLabel": market_memory.data_quality_label,
                    "latestFinalCandleTime": iso_or_none(market_memory.latest_final_candle_time),
                }
                if market_memory is not None
                else None
            ),
            "latestDataQualityRun": (
                {
                    "id": str(latest_data_quality_run.id),
                    "qualityLabel": latest_data_quality_run.quality_label,
                    "findingCount": latest_data_quality_run.finding_count,
                    "qualityScore": str(latest_data_quality_run.quality_score),
                }
                if latest_data_quality_run is not None
                else None
            ),
            "policy": {
                "doesNotFetchExternalProviders": True,
                "doesNotMutateCandles": True,
                "doesNotCreatePollingRequestsAutomatically": True,
                "noBrokerExecution": True,
                "noFinancialAdvice": True,
            },
        }
        summary = build_summary(
            data_source=data_source,
            freshness_label=freshness_label,
            missing_candle_count=missing_candle_count,
            consecutive_failure_count=consecutive_failure_count,
            live_status=live_subscription.status if live_subscription is not None else None,
            data_quality_label=(
                latest_data_quality_run.quality_label
                if latest_data_quality_run is not None
                else None
            ),
        )
        return SnapshotInputs(
            data_source=data_source,
            latest_final_candle_time=(
                latest_final_candle.timestamp if latest_final_candle is not None else None
            ),
            latest_successful_poll_at=poll_completed_at(latest_successful_poll),
            latest_failed_poll_at=poll_completed_at(latest_failed_poll),
            latest_gap_recovery_plan_id=latest_gap_plan.id if latest_gap_plan is not None else None,
            latest_data_quality_run_id=(
                latest_data_quality_run.id if latest_data_quality_run is not None else None
            ),
            consecutive_failure_count=consecutive_failure_count,
            missing_candle_count=missing_candle_count,
            freshness_label=freshness_label,
            stale_seconds=stale_seconds,
            summary=summary,
            metadata_json=metadata_json,
        )

    async def calculate_quality_report(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        window: HealthWindow,
    ) -> CandleQualityReport:
        candles = await self.repository.list_candles_in_window(
            workspace_id=workspace_id,
            source_id=source_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            start_time=window.start_time,
            end_time=window.end_time,
        )
        return calculate_candle_quality(
            candles=[
                CandleQualityInput(timestamp=candle.timestamp, is_final=candle.is_final)
                for candle in candles
            ],
            timeframe=Timeframe(timeframe),
            start_time=window.start_time,
            end_time=window.end_time,
        )

    async def validate_identity(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None,
        timeframe: str | None,
    ) -> None:
        await self.load_data_source(workspace_id, source_id)
        if symbol_id is None and timeframe is not None:
            raise AppError(
                422,
                "provider_health_timeframe_requires_symbol",
                "Provider health timeframe scope requires a symbol",
            )
        if symbol_id is not None:
            symbol = await self.symbol_repository.get_by_id(symbol_id)
            if symbol is None:
                raise AppError(404, "symbol_not_found", "Symbol not found")
            if not symbol.is_active:
                raise AppError(422, "inactive_symbol", "Inactive symbols cannot be checked")
        if timeframe is not None:
            Timeframe(timeframe)

    async def load_data_source(self, workspace_id: UUID, source_id: UUID) -> DataSource:
        data_source = await self.data_source_repository.get_by_id(source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if data_source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )
        return data_source

    def determine_status(self, inputs: SnapshotInputs) -> ProviderHealthStatus:
        if inputs.data_source.status == DataSourceStatus.FAILED.value:
            return ProviderHealthStatus.FAILING
        if inputs.data_source.status == DataSourceStatus.INACTIVE.value:
            return ProviderHealthStatus.UNAVAILABLE
        if inputs.consecutive_failure_count >= self.settings.provider_health_max_failures_failing:
            return ProviderHealthStatus.FAILING
        if inputs.consecutive_failure_count >= self.settings.provider_health_max_failures_degraded:
            return ProviderHealthStatus.DEGRADED
        if inputs.freshness_label == ProviderHealthFreshnessLabel.STALE:
            return ProviderHealthStatus.STALE
        if inputs.freshness_label == ProviderHealthFreshnessLabel.NO_DATA:
            return ProviderHealthStatus.UNAVAILABLE
        if inputs.missing_candle_count > 0:
            return ProviderHealthStatus.DEGRADED
        data_quality = nested_get(inputs.metadata_json, "latestDataQualityRun", "qualityLabel")
        degraded_quality_labels = {
            DataQualityLabel.DEGRADED.value,
            DataQualityLabel.POOR.value,
            DataQualityLabel.INSUFFICIENT_DATA.value,
        }
        if data_quality in degraded_quality_labels:
            return ProviderHealthStatus.DEGRADED
        live_status = nested_get(inputs.metadata_json, "latestLiveSubscription", "status")
        degraded_live_statuses = {
            LiveFeedSubscriptionStatus.FAILED.value,
            LiveFeedSubscriptionStatus.STALE.value,
        }
        if live_status in degraded_live_statuses:
            return ProviderHealthStatus.DEGRADED
        if inputs.latest_final_candle_time is None and inputs.latest_successful_poll_at is None:
            return ProviderHealthStatus.UNKNOWN
        return ProviderHealthStatus.HEALTHY

    def determine_freshness_label(
        self,
        latest_final_candle_time: datetime | None,
        timeframe: str | None,
    ) -> ProviderHealthFreshnessLabel:
        if timeframe is None:
            return ProviderHealthFreshnessLabel.UNKNOWN
        if latest_final_candle_time is None:
            return ProviderHealthFreshnessLabel.NO_DATA
        age_seconds = self.calculate_stale_seconds(latest_final_candle_time)
        if age_seconds is None:
            return ProviderHealthFreshnessLabel.UNKNOWN
        threshold = self.freshness_threshold_seconds(timeframe)
        if threshold <= 0:
            return ProviderHealthFreshnessLabel.UNKNOWN
        if age_seconds <= threshold:
            return ProviderHealthFreshnessLabel.FRESH
        if age_seconds <= threshold * 2:
            return ProviderHealthFreshnessLabel.DELAYED
        return ProviderHealthFreshnessLabel.STALE

    def freshness_threshold_seconds(self, timeframe: str) -> int:
        match timeframe:
            case Timeframe.ONE_MINUTE.value:
                return self.settings.provider_health_fresh_seconds_1m
            case Timeframe.FIVE_MINUTES.value:
                return self.settings.provider_health_fresh_seconds_5m
            case Timeframe.FIFTEEN_MINUTES.value:
                return self.settings.provider_health_fresh_seconds_15m
            case Timeframe.ONE_HOUR.value:
                return self.settings.provider_health_fresh_seconds_1h
            case _:
                try:
                    return max(int(timeframe_duration(Timeframe(timeframe)).total_seconds() * 2), 1)
                except ValueError:
                    return 0

    def calculate_stale_seconds(self, latest_final_candle_time: datetime | None) -> int | None:
        if latest_final_candle_time is None:
            return None
        normalized = normalize_datetime(latest_final_candle_time)
        seconds = int((utc_now() - normalized).total_seconds())
        return max(seconds, 0)

    def health_window(
        self,
        timeframe: str,
        latest_final_candle_time: datetime | None,
    ) -> HealthWindow:
        duration = timeframe_duration(Timeframe(timeframe))
        end_time = latest_final_candle_time or floor_datetime(utc_now(), duration)
        normalized_end = floor_datetime(normalize_datetime(end_time), duration)
        return HealthWindow(
            start_time=normalized_end - (duration * 119),
            end_time=normalized_end,
        )

    def gap_recovery_window(self, snapshot: ProviderHealthSnapshot) -> HealthWindow:
        window = snapshot.metadata_json.get("qualityWindow")
        if isinstance(window, dict):
            start = parse_datetime(window.get("startTime"))
            end = parse_datetime(window.get("endTime"))
            if start is not None and end is not None:
                return HealthWindow(start_time=start, end_time=end)
        if snapshot.timeframe is None:
            raise AppError(
                422,
                "provider_health_snapshot_missing_timeframe",
                "Provider health snapshot has no timeframe",
            )
        return self.health_window(snapshot.timeframe, snapshot.latest_final_candle_time)


def snapshot_is_current(snapshot: ProviderHealthSnapshot) -> bool:
    return snapshot.created_at >= utc_now() - timedelta(seconds=30)


def count_status(snapshots: list[ProviderHealthSnapshot], status: ProviderHealthStatus) -> int:
    return sum(1 for snapshot in snapshots if snapshot.status == status.value)


def count_freshness(
    snapshots: list[ProviderHealthSnapshot],
    freshness: ProviderHealthFreshnessLabel,
) -> int:
    return sum(1 for snapshot in snapshots if snapshot.freshness_label == freshness.value)


def count_consecutive_failures(requests: list[object]) -> int:
    count = 0
    for request in requests:
        status = getattr(request, "status", None)
        if status == ProviderPollingRequestStatus.FAILED.value:
            count += 1
            continue
        if status in {
            ProviderPollingRequestStatus.COMPLETED.value,
            ProviderPollingRequestStatus.COMPLETED_WITH_WARNINGS.value,
        }:
            break
    return count


def poll_completed_at(request: object | None) -> datetime | None:
    if request is None:
        return None
    completed_at = getattr(request, "completed_at", None)
    created_at = getattr(request, "created_at", None)
    return completed_at or created_at


def compact_polling_request(request: ProviderPollingRequest | None) -> dict[str, object] | None:
    if request is None:
        return None
    return {
        "id": str(request.id),
        "status": request.status,
        "provider": request.provider,
        "providerSymbol": request.provider_symbol,
        "timeframe": request.timeframe,
        "receivedCandleCount": request.received_candle_count,
        "storedCandleCount": request.stored_candle_count,
        "skippedCandleCount": request.skipped_candle_count,
        "errorMessage": request.error_message,
        "createdAt": iso_or_none(request.created_at),
        "completedAt": iso_or_none(request.completed_at),
    }


def build_summary(
    data_source: DataSource,
    freshness_label: ProviderHealthFreshnessLabel,
    missing_candle_count: int,
    consecutive_failure_count: int,
    live_status: str | None,
    data_quality_label: str | None,
) -> str:
    parts: list[str] = [f"Provider {data_source.provider} source is {data_source.status}."]
    if freshness_label == ProviderHealthFreshnessLabel.FRESH:
        parts.append("Data fresh.")
    elif freshness_label == ProviderHealthFreshnessLabel.DELAYED:
        parts.append("Data delayed.")
    elif freshness_label == ProviderHealthFreshnessLabel.STALE:
        parts.append("Data stale.")
    elif freshness_label == ProviderHealthFreshnessLabel.NO_DATA:
        parts.append("No final candle data.")
    if missing_candle_count > 0:
        parts.append(f"Missing candles: {missing_candle_count}.")
    if consecutive_failure_count > 0:
        parts.append(f"Recent provider failures: {consecutive_failure_count}.")
    if live_status:
        parts.append(f"Live subscription {live_status}.")
    if data_quality_label:
        parts.append(f"Data quality {data_quality_label}.")
    return " ".join(parts)


def nested_get(value: dict[str, object], *keys: str) -> object | None:
    current: object = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def floor_datetime(value: datetime, duration: timedelta) -> datetime:
    normalized = normalize_datetime(value)
    seconds = int(duration.total_seconds())
    epoch_seconds = int(normalized.timestamp())
    floored = epoch_seconds - (epoch_seconds % seconds)
    return datetime.fromtimestamp(floored, tz=UTC)


def parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return normalize_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def iso_or_none(value: datetime | None) -> str | None:
    return normalize_datetime(value).isoformat() if value is not None else None


def gap_service_plan_read(plan: object | None) -> object | None:
    if plan is None:
        return None
    from app.modules.candle_gap_recovery.schemas import CandleGapRecoveryPlanRead

    return CandleGapRecoveryPlanRead.model_validate(plan)
