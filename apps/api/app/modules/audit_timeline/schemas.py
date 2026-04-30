from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiSchema


class AuditTimelineSubjectType(StrEnum):
    ANALYSIS_RUN = "analysis_run"
    SIGNAL = "signal"
    REASONING_RUN = "reasoning_run"
    ACTION_PLAN = "action_plan"
    OUTCOME = "outcome"
    CHART_SCREENSHOT_RUN = "chart_screenshot_run"
    REPLAY = "replay"


class AuditTimelineSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ArtifactRelationship(StrEnum):
    PRODUCED = "produced"
    DERIVED_FROM = "derived_from"
    EXPLAINED_BY = "explained_by"
    REVIEWED_BY = "reviewed_by"
    REPLAYED_FROM = "replayed_from"
    EVALUATED_BY = "evaluated_by"
    CORRELATED_WITH = "correlated_with"
    PLANNED_ACTION = "planned_action"


class CompletenessLabel(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    SPARSE = "sparse"


class AuditTimelineSubject(ApiSchema):
    type: AuditTimelineSubjectType
    id: UUID


class AuditTimelineCompleteness(ApiSchema):
    score: float = Field(ge=0, le=1)
    label: CompletenessLabel
    missing_sections: list[str] = Field(default_factory=list)


class AuditTimelineEvent(ApiSchema):
    event_time: datetime
    event_type: str
    source_type: str
    source_id: str
    title: str
    summary: str
    severity: AuditTimelineSeverity = AuditTimelineSeverity.INFO
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactNode(ApiSchema):
    id: str
    type: str
    label: str
    status: str | None = None


class ArtifactEdge(ApiSchema):
    from_: str = Field(alias="from")
    to: str
    relationship: ArtifactRelationship


class ArtifactGraph(ApiSchema):
    nodes: list[ArtifactNode] = Field(default_factory=list)
    edges: list[ArtifactEdge] = Field(default_factory=list)


class AuditTimelineRead(ApiSchema):
    subject: AuditTimelineSubject
    workspace_id: UUID
    generated_at: datetime
    completeness: AuditTimelineCompleteness
    timeline: list[AuditTimelineEvent]
    artifact_graph: ArtifactGraph
    sections: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class AuditTimelineOptions(ApiSchema):
    include_audit: bool = True
    include_graph: bool = True
    include_artifacts: bool = True
    include_metadata: bool = True
    limit_events: int = Field(default=200, ge=1, le=500)
    limit_audit: int = Field(default=100, ge=1, le=500)
    limit_artifacts: int = Field(default=200, ge=1, le=500)
