from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candle_gap_recovery.schemas import (
    CandleGapRecoveryPlanRead,
    PrepareProviderPollingResponse,
)
from app.modules.candles.timeframes import Timeframe
from app.modules.provider_health.models import (
    ProviderHealthFreshnessLabel,
    ProviderHealthStatus,
)


class ProviderHealthSnapshotBuildRequest(ApiSchema):
    workspace_id: UUID
    source_id: UUID
    symbol_id: UUID | None = None
    timeframe: Timeframe | None = None
    force_recompute: bool = False


class ProviderHealthSnapshotListFilters(ApiSchema):
    workspace_id: UUID
    source_id: UUID | None = None
    symbol_id: UUID | None = None
    timeframe: Timeframe | None = None
    provider: str | None = None
    status: ProviderHealthStatus | None = None
    freshness_label: ProviderHealthFreshnessLabel | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ProviderHealthSnapshotRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    source_id: UUID
    provider: str
    symbol_id: UUID | None
    timeframe: str | None
    status: ProviderHealthStatus
    freshness_label: ProviderHealthFreshnessLabel
    latest_final_candle_time: datetime | None
    latest_successful_poll_at: datetime | None
    latest_failed_poll_at: datetime | None
    latest_gap_recovery_plan_id: UUID | None
    latest_data_quality_run_id: UUID | None
    consecutive_failure_count: int
    missing_candle_count: int
    stale_seconds: int | None
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ProviderHealthSummary(ApiSchema):
    workspace_id: UUID
    total_snapshots: int
    healthy_count: int
    degraded_count: int
    stale_count: int
    failing_count: int
    unavailable_count: int
    unknown_count: int
    fresh_count: int
    delayed_count: int
    no_data_count: int
    missing_candle_count: int
    provider_failure_count: int
    ready_for_deterministic_analysis_count: int
    latest_snapshot_at: datetime | None


class ProviderHealthWorkspaceRefreshResponse(ApiSchema):
    workspace_id: UUID
    requested_limit: int
    refreshed_count: int
    skipped_count: int
    snapshots: list[ProviderHealthSnapshotRead]


class ProviderHealthPrepareGapRecoveryRequest(ApiSchema):
    create_requests: bool = False


class ProviderHealthPrepareGapRecoveryResponse(ApiSchema):
    snapshot: ProviderHealthSnapshotRead
    recovery_plan: CandleGapRecoveryPlanRead | None
    preparation: PrepareProviderPollingResponse | None
    created_plan: bool
