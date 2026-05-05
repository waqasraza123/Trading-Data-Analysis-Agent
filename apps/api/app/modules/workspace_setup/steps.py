from enum import StrEnum


class WorkspaceSetupStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkspaceSetupStepKey(StrEnum):
    WORKSPACE = "workspace"
    USER = "user"
    SYMBOLS = "symbols"
    DATA_SOURCE = "data_source"
    CREDENTIAL_REFERENCE = "credential_reference"
    WATCHLIST = "watchlist"
    SCANNER_PRESET = "scanner_preset"
    PREFERENCE_PROFILE = "preference_profile"
    DEMO_DATA = "demo_data"
    READINESS_CHECK = "readiness_check"
    FIRST_SCAN = "first_scan"


class WorkspaceSetupStepStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


SETUP_STEP_ORDER: tuple[WorkspaceSetupStepKey, ...] = (
    WorkspaceSetupStepKey.WORKSPACE,
    WorkspaceSetupStepKey.USER,
    WorkspaceSetupStepKey.SYMBOLS,
    WorkspaceSetupStepKey.DATA_SOURCE,
    WorkspaceSetupStepKey.CREDENTIAL_REFERENCE,
    WorkspaceSetupStepKey.WATCHLIST,
    WorkspaceSetupStepKey.SCANNER_PRESET,
    WorkspaceSetupStepKey.PREFERENCE_PROFILE,
    WorkspaceSetupStepKey.DEMO_DATA,
    WorkspaceSetupStepKey.READINESS_CHECK,
    WorkspaceSetupStepKey.FIRST_SCAN,
)

OPTIONAL_SETUP_STEPS: set[WorkspaceSetupStepKey] = {
    WorkspaceSetupStepKey.CREDENTIAL_REFERENCE,
    WorkspaceSetupStepKey.SCANNER_PRESET,
    WorkspaceSetupStepKey.PREFERENCE_PROFILE,
    WorkspaceSetupStepKey.DEMO_DATA,
    WorkspaceSetupStepKey.READINESS_CHECK,
    WorkspaceSetupStepKey.FIRST_SCAN,
}


def next_step_after(completed_or_skipped_steps: set[str]) -> WorkspaceSetupStepKey | None:
    for step in SETUP_STEP_ORDER:
        if step.value not in completed_or_skipped_steps:
            return step
    return None
