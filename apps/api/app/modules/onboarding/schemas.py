from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiSchema


class OnboardingReadinessLabel(StrEnum):
    READY = "ready"
    NEEDS_SETUP = "needs_setup"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class OnboardingDataFreshnessLabel(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    NO_DATA = "no_data"
    UNKNOWN = "unknown"


class OnboardingStepState(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    WARNING = "warning"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"


class OnboardingActionType(StrEnum):
    CREATE_WORKSPACE = "create_workspace"
    CREATE_USER = "create_user"
    SEED_SYMBOLS = "seed_symbols"
    SEED_DEFAULT_DATA_SOURCES = "seed_default_data_sources"
    CREATE_BASIC_WATCHLIST = "create_basic_watchlist"
    CREATE_BASIC_SCAN_CONFIG = "create_basic_scan_config"
    RUN_READINESS_CHECK = "run_readiness_check"
    RUN_DEMO_FLOW = "run_demo_flow"


class OnboardingNextStepKey(StrEnum):
    CREATE_WORKSPACE = "create_workspace"
    CREATE_USER = "create_user"
    SEED_SYMBOLS = "seed_symbols"
    CONFIGURE_DATA_SOURCE = "configure_data_source"
    VERIFY_DATA = "verify_data"
    CREATE_WATCHLIST = "create_watchlist"
    CREATE_SCAN_CONFIG = "create_scan_config"
    RUN_READINESS = "run_readiness"
    OPEN_COMMAND_CENTER = "open_command_center"
    RUN_DEMO = "run_demo"


class OnboardingStatusSummary(ApiSchema):
    readiness_label: OnboardingReadinessLabel
    readiness_score: float = Field(ge=0, le=1)
    summary: str


class OnboardingWorkspaceStatus(ApiSchema):
    exists: bool
    workspace_id: UUID | None = None
    name: str | None = None


class OnboardingUserStatus(ApiSchema):
    exists: bool
    user_id: UUID | None = None
    role: str | None = None


class OnboardingCountStatus(ApiSchema):
    configured: bool
    count: int = Field(ge=0)
    missing: bool = False


class OnboardingDataSourcesStatus(OnboardingCountStatus):
    provider_ready: bool = False


class OnboardingDataFreshnessStatus(ApiSchema):
    label: OnboardingDataFreshnessLabel
    summary: str


class OnboardingDailyWorkflowStatus(ApiSchema):
    available: bool
    last_run_status: str | None = None


class OnboardingDemoModeStatus(ApiSchema):
    available: bool
    enabled: bool


class OnboardingNextStep(ApiSchema):
    key: OnboardingNextStepKey
    title: str
    description: str
    route: str
    action_type: OnboardingActionType | None = None


class OnboardingStep(ApiSchema):
    key: str
    title: str
    description: str
    state: OnboardingStepState
    route: str
    action_type: OnboardingActionType | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OnboardingStatusResponse(ApiSchema):
    status: OnboardingStatusSummary
    workspace: OnboardingWorkspaceStatus
    user: OnboardingUserStatus
    symbols: OnboardingCountStatus
    data_sources: OnboardingDataSourcesStatus
    data_freshness: OnboardingDataFreshnessStatus
    watchlists: OnboardingCountStatus
    scan_configs: OnboardingCountStatus
    daily_workflow: OnboardingDailyWorkflowStatus
    demo_mode: OnboardingDemoModeStatus
    next_step: OnboardingNextStep
    steps: list[OnboardingStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)


class OnboardingActionRequest(ApiSchema):
    action_type: OnboardingActionType
    workspace_id: UUID | None = None
    user_id: UUID | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class OnboardingActionResponse(ApiSchema):
    action_type: OnboardingActionType
    status: str
    message: str
    workspace_id: UUID | None = None
    user_id: UUID | None = None
    artifact_ids: dict[str, UUID | list[UUID] | None] = Field(default_factory=dict)
    onboarding_status: OnboardingStatusResponse | None = None
