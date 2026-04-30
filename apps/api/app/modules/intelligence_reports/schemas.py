from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiSchema


class IntelligenceReportType(StrEnum):
    SIGNAL_REPORT = "signal_report"
    ANALYSIS_RUN_REPORT = "analysis_run_report"
    REASONING_RUN_REPORT = "reasoning_run_report"
    OUTCOME_REPORT = "outcome_report"
    SCREENSHOT_DECISION_REPORT = "screenshot_decision_report"


class IntelligenceReportSubjectType(StrEnum):
    SIGNAL = "signal"
    ANALYSIS_RUN = "analysis_run"
    REASONING_RUN = "reasoning_run"
    OUTCOME = "outcome"
    SCREENSHOT_DECISION = "screenshot_decision"


class IntelligenceReportSubject(ApiSchema):
    type: IntelligenceReportSubjectType
    id: UUID


class IntelligenceReportRead(ApiSchema):
    report_type: IntelligenceReportType
    generated_at: datetime
    workspace_id: UUID
    subject: IntelligenceReportSubject
    sections: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)


class IntelligenceReportOptions(ApiSchema):
    include_audit: bool = True
    include_reasoning: bool = True
    include_actions: bool = True
    include_outcomes: bool = True
    include_diagnostics: bool = True
    limit_audit: int = Field(default=100, ge=1, le=500)
    limit_evidence: int = Field(default=50, ge=1, le=500)
