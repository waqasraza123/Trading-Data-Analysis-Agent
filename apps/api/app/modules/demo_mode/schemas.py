from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiSchema

DEMO_MODE_SAFETY_NOTICES = [
    "Demo mode uses synthetic deterministic candles only.",
    "Demo mode does not connect to brokers or execute orders.",
    "Demo mode does not auto-trade, copy-trade, or send financial advice.",
    "Generated records are labeled as demo artifacts where the existing model supports metadata.",
]


class DemoModeWorkspaceRequest(ApiSchema):
    workspace_name: str | None = Field(default=None, min_length=1, max_length=120)
    symbols: list[str] | None = None
    timeframes: list[str] | None = None

    @field_validator("workspace_name")
    @classmethod
    def normalize_workspace_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("symbols", "timeframes")
    @classmethod
    def normalize_text_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [item.strip().upper() for item in value if item.strip()]
        return list(dict.fromkeys(normalized))


class DemoModeRunRequest(DemoModeWorkspaceRequest):
    workspace_id: UUID | None = None
    include_journal_entry: bool = True
    force_recompute: bool = False


class DemoModeArtifactLink(ApiSchema):
    label: str
    href: str
    artifact_type: str
    artifact_id: str | None = None


class DemoModeStatusResponse(ApiSchema):
    enabled: bool
    status: str
    app_env: str
    reason: str | None = None
    default_workspace_name: str
    default_symbols: list[str]
    default_timeframes: list[str]
    safety_notices: list[str] = Field(default_factory=lambda: DEMO_MODE_SAFETY_NOTICES.copy())


class DemoModeWorkspaceResponse(ApiSchema):
    enabled: bool
    status: str
    message: str
    workspace_id: UUID | None = None
    user_id: UUID | None = None
    source_id: UUID | None = None
    symbols: list[dict[str, Any]] = Field(default_factory=list)
    timeframes: list[str] = Field(default_factory=list)
    links: list[DemoModeArtifactLink] = Field(default_factory=list)
    safety_notices: list[str] = Field(default_factory=lambda: DEMO_MODE_SAFETY_NOTICES.copy())


class DemoModeFlowStep(ApiSchema):
    key: str
    status: str
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DemoModeRunFullFlowResponse(DemoModeWorkspaceResponse):
    import_batch_ids: list[UUID] = Field(default_factory=list)
    analysis_run_ids: list[UUID] = Field(default_factory=list)
    signal_ids: list[UUID] = Field(default_factory=list)
    setup_context_ids: list[UUID] = Field(default_factory=list)
    priority_score_ids: list[UUID] = Field(default_factory=list)
    outcome_ids: list[UUID] = Field(default_factory=list)
    watchlist_id: UUID | None = None
    scan_config_id: UUID | None = None
    scan_run_id: UUID | None = None
    daily_brief_id: UUID | None = None
    journal_entry_id: UUID | None = None
    readiness_run_id: UUID | None = None
    steps: list[DemoModeFlowStep] = Field(default_factory=list)
