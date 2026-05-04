from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe
from app.modules.market_memory.models import (
    MarketMemoryDataQualityLabel,
    MarketMemoryFreshnessLabel,
)


class MarketMemorySnapshotBuildRequest(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None = None
    timeframe: Timeframe
    force_recompute: bool = False


class MarketMemorySnapshotListFilters(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID | None = None
    source_id: UUID | None = None
    timeframe: Timeframe | None = None
    freshness_label: MarketMemoryFreshnessLabel | None = None
    data_quality_label: MarketMemoryDataQualityLabel | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class RollingMarketStateSnapshotRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    state_version: str
    latest_final_candle_time: datetime | None
    latest_analysis_run_id: UUID | None
    latest_signal_id: UUID | None
    latest_outcome_id: UUID | None
    data_quality_label: MarketMemoryDataQualityLabel
    freshness_label: MarketMemoryFreshnessLabel
    trend_state: str | None
    volatility_state: str | None
    range_state: str | None
    market_regime_label: str | None
    market_session_label: str | None
    multi_timeframe_label: str | None
    cross_asset_label: str | None
    latest_signal_bias: str | None
    latest_signal_pattern_type: str | None
    latest_signal_confidence_label: str | None
    context_json: dict[str, Any]
    warnings_json: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class MarketMemoryWorkspaceRefreshResponse(ApiSchema):
    workspace_id: UUID
    requested_limit: int
    refreshed_count: int
    skipped_count: int
    snapshots: list[RollingMarketStateSnapshotRead]
