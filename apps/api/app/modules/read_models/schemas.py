from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema


class DashboardSymbolReadModelFilters(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID | None = None
    source_id: UUID | None = None
    timeframe: str | None = None
    freshness_label: str | None = None
    data_quality_label: str | None = None
    limit: int = Field(default=200, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class SignalCardReadModelFilters(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID | None = None
    timeframe: str | None = None
    classification_status: str | None = None
    bias: str | None = None
    review_bucket: str | None = None
    priority_label: str | None = None
    freshness_label: str | None = None
    data_quality_label: str | None = None
    readiness_label: str | None = None
    search: str | None = None
    limit: int = Field(default=200, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class RebuildSymbolReadModelRequest(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID
    timeframe: str
    source_id: UUID | None = None


class RebuildWorkspaceSignalCardsRequest(ApiSchema):
    workspace_id: UUID
    limit: int = Field(default=500, ge=1, le=1000)


class RebuildCommandCenterRequest(ApiSchema):
    workspace_id: UUID
    period_start: datetime | None = None
    period_end: datetime | None = None


class DashboardSymbolReadModelRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    read_model_version: str
    latest_final_candle_time: datetime | None
    freshness_label: str | None
    data_quality_label: str | None
    latest_signal_id: UUID | None
    latest_bias: str | None
    latest_pattern_type: str | None
    latest_confidence_label: str | None
    latest_priority_score: Decimal | None
    latest_priority_label: str | None
    setup_quality_label: str | None
    market_regime_label: str | None
    market_session_label: str | None
    pending_action_count: int
    warning_count: int
    summary_json: dict[str, Any]
    updated_at: datetime
    created_at: datetime


class SignalCardReadModelRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    signal_id: UUID
    analysis_run_id: UUID
    symbol_id: UUID
    timeframe: str
    read_model_version: str
    classification_status: str
    bias: str
    pattern_type: str | None
    confidence_score: Decimal | None
    confidence_label: str | None
    priority_score: Decimal | None
    priority_label: str | None
    review_bucket: str | None
    setup_quality_label: str | None
    freshness_label: str | None
    data_quality_label: str | None
    readiness_label: str | None
    outcome_summary_json: dict[str, Any]
    evidence_summary_json: dict[str, Any]
    risk_summary_json: dict[str, Any]
    action_summary_json: dict[str, Any]
    warning_summary_json: dict[str, Any]
    searchable_text: str
    updated_at: datetime
    created_at: datetime


class CommandCenterReadModelRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    read_model_version: str
    period_start: datetime | None
    period_end: datetime | None
    status: str
    summary_json: dict[str, Any]
    sections_json: dict[str, Any]
    warning_count: int
    generated_at: datetime
    created_at: datetime
    updated_at: datetime


class RebuildWorkspaceSignalCardsResponse(ApiSchema):
    workspace_id: UUID
    requested_limit: int
    rebuilt_count: int
    skipped_count: int
    cards: list[SignalCardReadModelRead]
