from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema


class WorkspaceOverviewQuery(ApiSchema):
    period_start: datetime | None = None
    period_end: datetime | None = None
    watchlist_id: UUID | None = None
    preference_profile_id: UUID | None = None
    include_read_models: bool = True
    include_notifications: bool = True
    include_journal: bool = True
    include_quality: bool = True


class WorkspaceOverviewStatus(ApiReadSchema):
    status: str
    label: str
    summary: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorkspaceOverviewItem(ApiReadSchema):
    id: str
    title: str
    summary: str
    reason: str | None = None
    symbol_id: UUID | None = None
    symbol: str | None = None
    timeframe: str | None = None
    signal_id: UUID | None = None
    analysis_run_id: UUID | None = None
    bias: str | None = None
    confidence_label: str | None = None
    priority_label: str | None = None
    setup_quality_label: str | None = None
    freshness_label: str | None = None
    data_quality_label: str | None = None
    href: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorkspaceOverviewNotificationSummary(ApiReadSchema):
    unread_count: int = 0
    acknowledged_count: int = 0
    latest: list[WorkspaceOverviewItem] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorkspaceOverviewResponse(ApiReadSchema):
    workspace_id: UUID
    generated_at: datetime
    overview_version: str
    readiness: WorkspaceOverviewStatus
    data_freshness: WorkspaceOverviewStatus
    provider_health: WorkspaceOverviewStatus
    daily_brief: WorkspaceOverviewStatus
    workflow: WorkspaceOverviewStatus
    review_first: list[WorkspaceOverviewItem] = Field(default_factory=list)
    needs_confirmation: list[WorkspaceOverviewItem] = Field(default_factory=list)
    avoid_conditions: list[WorkspaceOverviewItem] = Field(default_factory=list)
    outcome_updates: list[WorkspaceOverviewItem] = Field(default_factory=list)
    pending_actions: list[WorkspaceOverviewItem] = Field(default_factory=list)
    notifications: WorkspaceOverviewNotificationSummary
    journal_prompts: list[WorkspaceOverviewItem] = Field(default_factory=list)
    quality_warnings: list[WorkspaceOverviewItem] = Field(default_factory=list)
    navigation_hints: list[WorkspaceOverviewItem] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
