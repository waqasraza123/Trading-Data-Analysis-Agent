from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema


class HistoricalCaseSearchFilters(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID | None = None
    timeframe: str | None = None
    strategy_profile_key: str | None = None
    pattern_type: str | None = None
    bias: str | None = None
    classification_status: str | None = None
    min_score: Decimal | None = Field(default=None, ge=0, le=1)
    include_outcomes: bool = False
    exclude_same_signal: bool = True


class HistoricalCaseVectorBuildRequest(ApiSchema):
    force_recompute: bool = False


class HistoricalCaseBackfillRequest(ApiSchema):
    workspace_id: UUID
    limit: int = Field(ge=1)
    force_recompute: bool = False


class HistoricalCaseSearchRequest(ApiSchema):
    filters: HistoricalCaseSearchFilters
    limit: int | None = Field(default=None, ge=1)


class HistoricalCaseVectorRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID
    signal_id: UUID
    symbol_id: UUID
    timeframe: str
    strategy_profile_key: str | None
    strategy_profile_version: str | None
    pattern_type: str | None
    bias: str
    classification_status: str
    confidence_score: Decimal | None
    vector_version: str
    vector_json: dict[str, Any]
    feature_summary_json: dict[str, Any]
    indicator_summary_json: dict[str, Any]
    outcome_summary_json: dict[str, Any] | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class HistoricalCaseSignalSummary(ApiSchema):
    signal_id: UUID
    symbol_id: UUID
    timeframe: str
    strategy_profile_key: str | None
    strategy_profile_version: str | None
    pattern_type: str | None
    bias: str
    classification_status: str
    confidence_score: Decimal | None
    confidence_label: str | None
    summary: str | None


class HistoricalCaseSearchResult(ApiSchema):
    matched_signal_id: UUID
    analysis_run_id: UUID
    similarity_score: Decimal
    matched_reasons: list[str]
    differing_reasons: list[str]
    signal_summary: HistoricalCaseSignalSummary
    outcome_summary: dict[str, Any] | None = None
    deterministic_explanation_summary: str | None = None


class HistoricalCaseSearchRead(ApiSchema):
    source_signal_id: UUID | None
    source_analysis_run_id: UUID | None
    search_version: str
    result_count: int
    results: list[HistoricalCaseSearchResult]


class HistoricalCaseBackfillRead(ApiSchema):
    workspace_id: UUID
    vector_version: str
    requested_limit: int
    built_count: int
    skipped_count: int
    force_recompute: bool


class HistoricalCaseContextRead(ApiSchema):
    source_signal_id: UUID
    search_version: str
    cases: list[HistoricalCaseSearchResult]
