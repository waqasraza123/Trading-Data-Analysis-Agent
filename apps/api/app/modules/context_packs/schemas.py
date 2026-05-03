from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiSchema


class ContextPackSubjectType(StrEnum):
    SIGNAL = "signal"
    ANALYSIS_RUN = "analysis_run"
    REASONING_RUN = "reasoning_run"
    OUTCOME = "outcome"
    CHART_SCREENSHOT_RUN = "chart_screenshot_run"
    REPLAY = "replay"


class ContextPackSubject(ApiSchema):
    type: ContextPackSubjectType
    id: UUID


class ContextPackRead(ApiSchema):
    context_pack_version: str
    subject: ContextPackSubject
    workspace_id: UUID
    generated_at: datetime
    sections: dict[str, Any]
    missing_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    truncation: dict[str, Any] = Field(default_factory=dict)
    redaction: dict[str, Any] = Field(default_factory=dict)


class ContextPackOptions(ApiSchema):
    include_audit: bool = True
    include_reasoning: bool = True
    include_actions: bool = True
    include_outcomes: bool = True
    include_diagnostics: bool = True
    include_quality: bool = True
    include_reports: bool = True
    include_screenshots: bool = True
    max_evidence_rows: int | None = Field(default=None, ge=1, le=500)
    max_audit_events: int | None = Field(default=None, ge=1, le=1000)
    max_outcomes: int | None = Field(default=None, ge=1, le=500)
