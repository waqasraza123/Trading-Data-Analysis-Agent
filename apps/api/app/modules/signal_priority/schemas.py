from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.signal_priority.models import SignalPriorityLabel, SignalReviewBucket


class SignalPriorityListFilters(ApiSchema):
    workspace_id: UUID
    priority_label: SignalPriorityLabel | None = None
    review_bucket: SignalReviewBucket | None = None
    symbol_id: UUID | None = None
    timeframe: str | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class SignalPriorityScoreRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    signal_id: UUID
    analysis_run_id: UUID
    symbol_id: UUID
    timeframe: str
    priority_version: str
    priority_score: Decimal
    priority_label: SignalPriorityLabel
    review_bucket: SignalReviewBucket
    component_scores_json: dict[str, Any]
    penalties_json: list[dict[str, Any]]
    boosters_json: list[dict[str, Any]]
    reasons_json: list[dict[str, Any]]
    warnings_json: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class SignalPriorityWorkspaceScoreResponse(ApiSchema):
    workspace_id: UUID
    requested_limit: int
    scored_count: int
    skipped_count: int
    scores: list[SignalPriorityScoreRead]
