from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.candle_gap_recovery.detector import (
    CandleGapDetectionResult,
    CandleGapRange,
    CandleGapRecoveryDetector,
)
from app.modules.candle_gap_recovery.models import (
    CandleGapRecoveryItem,
    CandleGapRecoveryItemStatus,
    CandleGapRecoveryMethod,
    CandleGapRecoveryPlan,
    CandleGapRecoveryPlanStatus,
)
from app.modules.candle_gap_recovery.repository import CandleGapRecoveryRepository
from app.modules.candle_gap_recovery.schemas import (
    CandleGapRecoveryItemListQuery,
    CandleGapRecoveryPlanCreate,
    PreparedProviderPollingRequest,
    PrepareProviderPollingResponse,
)
from app.modules.candles.repository import CandleRepository
from app.modules.candles.timeframes import (
    Timeframe,
    normalize_timestamp,
    timestamp_aligns_with_timeframe,
)
from app.modules.data_sources.models import DataSource, DataSourceStatus, DataSourceType
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.provider_polling.adapters.registry import get_provider_polling_adapter
from app.modules.provider_polling.models import ProviderPollingRequest, ProviderPollingRequestStatus
from app.modules.provider_polling.repository import ProviderPollingRepository
from app.modules.provider_polling.schemas import ProviderPollingProvider
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository


TERMINAL_PLAN_STATUSES = {
    CandleGapRecoveryPlanStatus.COMPLETED.value,
    CandleGapRecoveryPlanStatus.COMPLETED_WITH_WARNINGS.value,
    CandleGapRecoveryPlanStatus.FAILED.value,
    CandleGapRecoveryPlanStatus.CANCELLED.value,
}


@dataclass(frozen=True)
class RecoveryMethodDecision:
    method: CandleGapRecoveryMethod
    provider: ProviderPollingProvider | None
    provider_symbol: str | None
    reason: str | None
    metadata_json: dict[str, object]


class CandleGapRecoveryService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = CandleGapRecoveryRepository(session)
        self.candle_repository = CandleRepository(session)
        self.detector = CandleGapRecoveryDetector(self.settings.candle_gap_recovery_max_gaps)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)
        self.provider_polling_repository = ProviderPollingRepository(session)

    async def create_recovery_plan(
        self,
        payload: CandleGapRecoveryPlanCreate,
    ) -> CandleGapRecoveryPlan:
        timeframe = payload.timeframe
        start_time = normalize_timestamp(payload.start_time)
        end_time = normalize_timestamp(payload.end_time)
        self.validate_detection_window(timeframe, start_time, end_time)
        symbol, source = await self.validate_symbol_and_source(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
        )
        candles = await self.candle_repository.fetch_window(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            timeframe=timeframe.value,
            start_time=start_time,
            end_time=end_time,
            source_id=payload.source_id,
            include_partial=False,
        )
        detection = self.detector.detect_missing_final_candles(
            candles=candles,
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
        )
        method_decisions = [
            self.resolve_recovery_method(gap, symbol, source)
            for gap in detection.gaps
        ]
        planned_request_count = sum(
            1
            for decision in method_decisions
            if decision.method == CandleGapRecoveryMethod.PROVIDER_POLLING
        )
        plan = CandleGapRecoveryPlan(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            timeframe=timeframe.value,
            status=(
                CandleGapRecoveryPlanStatus.READY.value
                if detection.gaps
                else CandleGapRecoveryPlanStatus.DRAFT.value
            ),
            recovery_version=self.settings.candle_gap_recovery_version,
            detection_start_time=start_time,
            detection_end_time=end_time,
            detected_gap_count=len(detection.gaps),
            planned_request_count=planned_request_count,
            completed_request_count=0,
            skipped_request_count=0,
            failed_request_count=0,
            summary=self.build_plan_summary(detection),
            metadata_json={
                **detection.metadata_json,
                "analysisQualityBlocked": bool(detection.gaps),
                "scheduledScansPotentiallyBlocked": bool(detection.gaps),
                "providerPollingPlannedRequestCount": planned_request_count,
                "providerPollingRequiresExplicitPrepare": True,
                "doesNotFetchExternalData": True,
            },
        )
        items = self.build_items(
            payload=payload,
            gaps=detection.gaps,
            method_decisions=method_decisions,
        )
        try:
            created_plan = await self.repository.create_plan(plan, items)
            await self.session.commit()
            await self.session.refresh(created_plan)
            return created_plan
        except Exception:
            await self.session.rollback()
            raise

    async def get_recovery_plan(self, plan_id: UUID) -> CandleGapRecoveryPlan:
        plan = await self.repository.get_plan(plan_id)
        if plan is None:
            raise AppError(404, "candle_gap_recovery_plan_not_found", "Recovery plan not found")
        return plan

    async def list_recovery_items(
        self,
        plan_id: UUID,
        query: CandleGapRecoveryItemListQuery,
    ) -> list[CandleGapRecoveryItem]:
        await self.get_recovery_plan(plan_id)
        return await self.repository.list_items(
            plan_id=plan_id,
            status=query.status.value if query.status is not None else None,
            limit=query.limit,
            offset=query.offset,
        )

    async def cancel_recovery_plan(self, plan_id: UUID) -> CandleGapRecoveryPlan:
        plan = await self.get_recovery_plan(plan_id)
        if plan.status in TERMINAL_PLAN_STATUSES:
            return plan
        cancelled = await self.repository.cancel_plan(plan)
        await self.session.commit()
        return cancelled

    async def prepare_provider_polling_requests(
        self,
        plan_id: UUID,
        create_requests: bool = False,
    ) -> PrepareProviderPollingResponse:
        plan = await self.get_recovery_plan(plan_id)
        if plan.status == CandleGapRecoveryPlanStatus.CANCELLED.value:
            raise AppError(
                422,
                "candle_gap_recovery_plan_cancelled",
                "Cancelled recovery plans cannot prepare polling requests",
            )
        items = await self.repository.list_items(
            plan_id=plan_id,
            status=None,
            limit=self.settings.candle_gap_recovery_max_gaps,
            offset=0,
        )
        prepared_requests: list[PreparedProviderPollingRequest] = []
        created_count = 0
        skipped_count = 0
        failed_count = 0
        for item in items:
            prepared = await self.prepare_provider_polling_item(
                plan=plan,
                item=item,
                create_request=create_requests,
            )
            prepared_requests.append(prepared)
            if prepared.provider_polling_request_id is not None:
                created_count += 1
            elif prepared.status == CandleGapRecoveryItemStatus.SKIPPED.value:
                skipped_count += 1
            elif prepared.status == CandleGapRecoveryItemStatus.FAILED.value:
                failed_count += 1
        if create_requests:
            plan.planned_request_count = sum(
                1 for request in prepared_requests if request.provider is not None
            )
            plan.skipped_request_count = skipped_count
            plan.failed_request_count = failed_count
            await self.repository.update_plan(plan)
            await self.session.commit()
            await self.session.refresh(plan)
        return PrepareProviderPollingResponse(
            plan_id=plan.id,
            create_requests=create_requests,
            prepared_request_count=sum(
                1 for request in prepared_requests if request.provider is not None
            ),
            created_request_count=created_count,
            skipped_request_count=skipped_count,
            failed_request_count=failed_count,
            requests=prepared_requests,
        )

    async def prepare_provider_polling_item(
        self,
        plan: CandleGapRecoveryPlan,
        item: CandleGapRecoveryItem,
        create_request: bool,
    ) -> PreparedProviderPollingRequest:
        if item.recovery_method != CandleGapRecoveryMethod.PROVIDER_POLLING.value:
            return await self.prepare_skipped_item(
                item,
                item.skip_reason or "provider_polling_not_available_for_gap",
                create_request,
            )
        source = await self.load_provider_polling_source(item)
        if source is None:
            return await self.prepare_skipped_item(
                item,
                "provider_polling_source_not_available",
                create_request,
            )
        try:
            provider = self.provider_from_source(source)
            provider_symbol = await self.provider_symbol_from_source(source, item.symbol_id)
        except (AppError, ValueError) as error:
            if create_request:
                item.status = CandleGapRecoveryItemStatus.FAILED.value
                item.error_message = self.safe_error_message(error)
                await self.repository.update_item(item)
            return PreparedProviderPollingRequest(
                recovery_item_id=item.id,
                provider_polling_request_id=item.provider_polling_request_id,
                status=item.status,
                recovery_method=CandleGapRecoveryMethod.PROVIDER_POLLING,
                source_id=item.source_id,
                timeframe=Timeframe(item.timeframe),
                start_time=item.gap_start_time,
                end_time=item.gap_end_time,
                limit=item.expected_candle_count,
                expected_candle_count=item.expected_candle_count,
                error_message=self.safe_error_message(error),
            )
        metadata_json = self.provider_request_metadata(plan, item)
        prepared = PreparedProviderPollingRequest(
            recovery_item_id=item.id,
            provider_polling_request_id=item.provider_polling_request_id,
            status=item.status,
            recovery_method=CandleGapRecoveryMethod.PROVIDER_POLLING,
            provider=provider,
            provider_symbol=provider_symbol,
            source_id=source.id,
            timeframe=Timeframe(item.timeframe),
            start_time=item.gap_start_time,
            end_time=item.gap_end_time,
            limit=item.expected_candle_count,
            expected_candle_count=item.expected_candle_count,
            request_metadata_json=metadata_json,
        )
        if not create_request or item.provider_polling_request_id is not None:
            return prepared
        try:
            polling_request = await self.provider_polling_repository.create_request(
                ProviderPollingRequest(
                    workspace_id=item.workspace_id,
                    source_id=source.id,
                    symbol_id=item.symbol_id,
                    provider=provider.value,
                    provider_symbol=provider_symbol,
                    timeframe=item.timeframe,
                    start_time=item.gap_start_time,
                    end_time=item.gap_end_time,
                    limit=item.expected_candle_count,
                    status=ProviderPollingRequestStatus.PENDING.value,
                    request_metadata_json=metadata_json,
                    response_metadata_json={},
                    received_candle_count=0,
                    stored_candle_count=0,
                    skipped_candle_count=0,
                )
            )
            item.provider_polling_request_id = polling_request.id
            item.status = CandleGapRecoveryItemStatus.QUEUED.value
            item.metadata_json = {
                **item.metadata_json,
                "providerPollingRequestId": str(polling_request.id),
            }
            await self.repository.update_item(item)
            prepared.provider_polling_request_id = polling_request.id
            prepared.status = CandleGapRecoveryItemStatus.QUEUED.value
            return prepared
        except (AppError, ValidationError, ValueError) as error:
            item.status = CandleGapRecoveryItemStatus.FAILED.value
            item.error_message = self.safe_error_message(error)
            await self.repository.update_item(item)
            prepared.status = CandleGapRecoveryItemStatus.FAILED.value
            prepared.error_message = item.error_message
            return prepared

    async def prepare_skipped_item(
        self,
        item: CandleGapRecoveryItem,
        reason: str,
        mutate: bool,
    ) -> PreparedProviderPollingRequest:
        if mutate and item.status == CandleGapRecoveryItemStatus.PLANNED.value:
            item.status = CandleGapRecoveryItemStatus.SKIPPED.value
            item.skip_reason = reason
            await self.repository.update_item(item)
        return PreparedProviderPollingRequest(
            recovery_item_id=item.id,
            provider_polling_request_id=item.provider_polling_request_id,
            status=item.status,
            recovery_method=CandleGapRecoveryMethod(item.recovery_method),
            source_id=item.source_id,
            timeframe=Timeframe(item.timeframe),
            start_time=item.gap_start_time,
            end_time=item.gap_end_time,
            limit=item.expected_candle_count,
            expected_candle_count=item.expected_candle_count,
            skip_reason=reason,
        )

    async def validate_symbol_and_source(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
    ) -> tuple[Symbol, DataSource | None]:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if not symbol.is_active:
            raise AppError(422, "inactive_symbol", "Inactive symbols cannot be planned")
        if source_id is None:
            return symbol, None
        source = await self.data_source_repository.get_by_id(source_id)
        if source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )
        return symbol, source

    def validate_detection_window(
        self,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        normalized_start = normalize_timestamp(start_time)
        normalized_end = normalize_timestamp(end_time)
        if normalized_start > normalized_end:
            raise AppError(
                422,
                "invalid_candle_gap_recovery_window",
                "start_time must be before end_time",
            )
        max_range = timedelta(days=self.settings.candle_gap_recovery_max_range_days)
        if normalized_end - normalized_start > max_range:
            raise AppError(
                422,
                "candle_gap_recovery_range_too_large",
                "Candle gap recovery detection range exceeds configured maximum",
            )
        if not timestamp_aligns_with_timeframe(
            normalized_start,
            timeframe,
        ) or not timestamp_aligns_with_timeframe(normalized_end, timeframe):
            raise AppError(
                422,
                "candle_gap_recovery_window_not_aligned",
                "start_time and end_time must align with timeframe",
            )

    def resolve_recovery_method(
        self,
        gap: CandleGapRange,
        symbol: Symbol,
        source: DataSource | None,
    ) -> RecoveryMethodDecision:
        if source is None:
            return RecoveryMethodDecision(
                method=CandleGapRecoveryMethod.MANUAL_IMPORT,
                provider=None,
                provider_symbol=None,
                reason="source_id_required_for_provider_polling",
                metadata_json={"providerPollingEligible": False},
            )
        if source.status != DataSourceStatus.ACTIVE.value:
            return RecoveryMethodDecision(
                method=CandleGapRecoveryMethod.UNAVAILABLE,
                provider=None,
                provider_symbol=None,
                reason="source_inactive",
                metadata_json={"providerPollingEligible": False},
            )
        if source.source_type != DataSourceType.API_POLLING.value:
            return RecoveryMethodDecision(
                method=CandleGapRecoveryMethod.MANUAL_IMPORT,
                provider=None,
                provider_symbol=None,
                reason="source_type_not_api_polling",
                metadata_json={"providerPollingEligible": False, "sourceType": source.source_type},
            )
        if gap.expected_candle_count > self.settings.provider_polling_max_candles_per_request:
            return RecoveryMethodDecision(
                method=CandleGapRecoveryMethod.MANUAL_IMPORT,
                provider=None,
                provider_symbol=None,
                reason="gap_exceeds_provider_polling_limit",
                metadata_json={
                    "providerPollingEligible": False,
                    "providerPollingMaxCandlesPerRequest": (
                        self.settings.provider_polling_max_candles_per_request
                    ),
                },
            )
        try:
            provider = ProviderPollingProvider(source.provider.strip().lower())
            get_provider_polling_adapter(provider.value)
        except (AppError, ValueError):
            return RecoveryMethodDecision(
                method=CandleGapRecoveryMethod.UNAVAILABLE,
                provider=None,
                provider_symbol=None,
                reason="unsupported_provider_polling_provider",
                metadata_json={
                    "providerPollingEligible": False,
                    "provider": source.provider,
                },
            )
        return RecoveryMethodDecision(
            method=CandleGapRecoveryMethod.PROVIDER_POLLING,
            provider=provider,
            provider_symbol=self.provider_symbol_from_config(source.config_json, symbol),
            reason=None,
            metadata_json={
                "providerPollingEligible": True,
                "provider": provider.value,
                "providerSymbol": self.provider_symbol_from_config(source.config_json, symbol),
            },
        )

    def build_items(
        self,
        payload: CandleGapRecoveryPlanCreate,
        gaps: list[CandleGapRange],
        method_decisions: list[RecoveryMethodDecision],
    ) -> list[CandleGapRecoveryItem]:
        return [
            CandleGapRecoveryItem(
                workspace_id=payload.workspace_id,
                symbol_id=payload.symbol_id,
                source_id=payload.source_id,
                timeframe=payload.timeframe.value,
                gap_start_time=gap.gap_start_time,
                gap_end_time=gap.gap_end_time,
                expected_candle_count=gap.expected_candle_count,
                status=CandleGapRecoveryItemStatus.PLANNED.value,
                recovery_method=decision.method.value,
                skip_reason=decision.reason,
                metadata_json={
                    **decision.metadata_json,
                    "gapStartTime": gap.gap_start_time.isoformat(),
                    "gapEndTime": gap.gap_end_time.isoformat(),
                    "expectedCandleCount": gap.expected_candle_count,
                    "blocksAnalysisQuality": True,
                    "blocksScheduledScans": True,
                    "doesNotMutateCandles": True,
                },
            )
            for gap, decision in zip(gaps, method_decisions, strict=True)
        ]

    async def load_provider_polling_source(
        self,
        item: CandleGapRecoveryItem,
    ) -> DataSource | None:
        if item.source_id is None:
            return None
        source = await self.data_source_repository.get_by_id(item.source_id)
        if source is None:
            return None
        if source.workspace_id != item.workspace_id:
            return None
        if source.source_type != DataSourceType.API_POLLING.value:
            return None
        if source.status != DataSourceStatus.ACTIVE.value:
            return None
        return source

    def provider_from_source(self, source: DataSource) -> ProviderPollingProvider:
        provider = ProviderPollingProvider(source.provider.strip().lower())
        get_provider_polling_adapter(provider.value)
        return provider

    async def provider_symbol_from_source(self, source: DataSource, symbol_id: UUID) -> str:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        return self.provider_symbol_from_config(source.config_json, symbol)

    def provider_symbol_from_config(self, config_json: dict[str, object], symbol: Symbol) -> str:
        provider_symbol = config_json.get("providerSymbol") or config_json.get("provider_symbol")
        if isinstance(provider_symbol, str) and provider_symbol.strip():
            return provider_symbol.strip()
        return symbol.symbol

    def provider_request_metadata(
        self,
        plan: CandleGapRecoveryPlan,
        item: CandleGapRecoveryItem,
    ) -> dict[str, Any]:
        return {
            "createdBy": "candle_gap_recovery",
            "recoveryPlanId": str(plan.id),
            "recoveryItemId": str(item.id),
            "gapStartTime": item.gap_start_time.isoformat(),
            "gapEndTime": item.gap_end_time.isoformat(),
            "expectedCandleCount": item.expected_candle_count,
            "doesNotExecutePolling": True,
        }

    def build_plan_summary(self, detection: CandleGapDetectionResult) -> str:
        if not detection.gaps:
            return "No missing final candles detected in the requested window."
        suffix = ""
        if detection.truncated_gap_count:
            suffix = f" {detection.truncated_gap_count} additional gap ranges were truncated."
        return (
            f"Detected {len(detection.gaps)} missing final candle gap range(s) covering "
            f"{detection.missing_candle_count} missing candle timestamp(s).{suffix}"
        )

    def safe_error_message(self, error: Exception) -> str:
        if isinstance(error, AppError):
            return error.message[:1000]
        if isinstance(error, ValidationError):
            return str(error.errors()[0]["msg"])[:1000]
        return type(error).__name__
