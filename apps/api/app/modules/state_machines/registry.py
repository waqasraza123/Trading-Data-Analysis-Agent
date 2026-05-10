from collections.abc import Iterable
from dataclasses import dataclass

DEFAULT_STATE_MACHINE_VERSION = "1.0.0"


@dataclass(frozen=True)
class StateTransitionDefinition:
    from_state: str
    to_state: str
    label: str | None = None

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "fromState": self.from_state,
            "toState": self.to_state,
        }
        if self.label is not None:
            payload["label"] = self.label
        return payload


@dataclass(frozen=True)
class StateMachineDefinitionSpec:
    key: str
    version: str
    object_type: str
    states: tuple[str, ...]
    transitions: tuple[StateTransitionDefinition, ...]
    terminal_states: tuple[str, ...]
    metadata: dict[str, object]

    def transition_pairs(self) -> set[tuple[str, str]]:
        return {(transition.from_state, transition.to_state) for transition in self.transitions}


def transition(
    from_state: str, to_state: str, label: str | None = None
) -> StateTransitionDefinition:
    return StateTransitionDefinition(from_state=from_state, to_state=to_state, label=label)


def transitions_from(
    from_state: str, to_states: Iterable[str]
) -> tuple[StateTransitionDefinition, ...]:
    return tuple(transition(from_state, to_state) for to_state in to_states)


DEFAULT_STATE_MACHINES: tuple[StateMachineDefinitionSpec, ...] = (
    StateMachineDefinitionSpec(
        key="import_batch",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="import_batch",
        states=(
            "pending",
            "processing",
            "completed",
            "completed_with_warnings",
            "failed",
            "cancelled",
        ),
        transitions=(
            transition("pending", "processing"),
            transition("pending", "cancelled"),
            transition("processing", "completed"),
            transition("processing", "completed_with_warnings"),
            transition("processing", "failed"),
            transition("processing", "cancelled"),
        ),
        terminal_states=("completed", "completed_with_warnings", "failed", "cancelled"),
        metadata={"source": "imports.models.ImportBatchStatus", "adoption": "optional"},
    ),
    StateMachineDefinitionSpec(
        key="live_feed_subscription",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="live_feed_subscription",
        states=("active", "paused", "failed", "stopped", "stale"),
        transitions=(
            transition("active", "paused"),
            transition("active", "stale"),
            transition("active", "failed"),
            transition("active", "stopped"),
            transition("paused", "active"),
            transition("paused", "stopped"),
            transition("stale", "active"),
            transition("stale", "failed"),
            transition("stale", "stopped"),
            transition("failed", "active"),
            transition("failed", "stopped"),
        ),
        terminal_states=("stopped",),
        metadata={"source": "live.models.LiveFeedSubscriptionStatus", "adoption": "optional"},
    ),
    StateMachineDefinitionSpec(
        key="analysis_run",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="analysis_run",
        states=("queued", "running", "completed", "failed", "insufficient_data", "cancelled"),
        transitions=(
            transition("queued", "running"),
            transition("queued", "cancelled"),
            transition("running", "completed"),
            transition("running", "failed"),
            transition("running", "insufficient_data"),
            transition("running", "cancelled"),
            transition("failed", "queued"),
            transition("insufficient_data", "queued"),
            transition("cancelled", "queued"),
        ),
        terminal_states=("completed",),
        metadata={"source": "analysis.models.AnalysisRunStatus", "adoption": "optional"},
    ),
    StateMachineDefinitionSpec(
        key="signal_classification",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="signal_classification",
        states=("signal", "no_signal", "unclear", "insufficient_evidence"),
        transitions=(),
        terminal_states=("signal", "no_signal", "unclear", "insufficient_evidence"),
        metadata={
            "source": "signals.models.SignalClassificationStatus",
            "adoption": "inspection_only",
            "notes": "Classification values are persisted results, not a mutating workflow.",
        },
    ),
    StateMachineDefinitionSpec(
        key="outcome_evaluation",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="outcome_evaluation",
        states=(
            "pending",
            "evaluated",
            "insufficient_future_data",
            "skipped_not_directional",
            "failed",
        ),
        transitions=transitions_from(
            "pending",
            ("evaluated", "insufficient_future_data", "skipped_not_directional", "failed"),
        ),
        terminal_states=(
            "evaluated",
            "insufficient_future_data",
            "skipped_not_directional",
            "failed",
        ),
        metadata={"source": "outcomes.models.OutcomeEvaluationStatus", "adoption": "optional"},
    ),
    StateMachineDefinitionSpec(
        key="reasoning_run",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="reasoning_run",
        states=(
            "pending",
            "completed",
            "failed",
            "blocked",
            "fallback_used",
            "provider_not_configured",
        ),
        transitions=transitions_from(
            "pending",
            ("completed", "failed", "blocked", "fallback_used", "provider_not_configured"),
        ),
        terminal_states=(
            "completed",
            "failed",
            "blocked",
            "fallback_used",
            "provider_not_configured",
        ),
        metadata={"source": "reasoning.models.ReasoningRunStatus", "adoption": "optional"},
    ),
    StateMachineDefinitionSpec(
        key="reasoning_action_item",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="reasoning_action_item",
        states=("pending", "due", "running", "completed", "skipped", "failed", "cancelled"),
        transitions=(
            transition("pending", "due"),
            transition("pending", "cancelled"),
            transition("due", "running"),
            transition("due", "skipped"),
            transition("due", "cancelled"),
            transition("running", "completed"),
            transition("running", "failed"),
            transition("failed", "due"),
            transition("failed", "cancelled"),
        ),
        terminal_states=("completed", "skipped", "cancelled"),
        metadata={
            "source": "action_plans.models.ReasoningActionItemStatus",
            "adoption": "optional",
        },
    ),
    StateMachineDefinitionSpec(
        key="operator_review_item",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="operator_review_item",
        states=("open", "acknowledged", "dismissed", "applied_manually"),
        transitions=transitions_from("open", ("acknowledged", "dismissed", "applied_manually")),
        terminal_states=("dismissed", "applied_manually"),
        metadata={
            "source": "profile_diagnostics.models.CalibrationRecommendationStatus",
            "adoption": "optional",
        },
    ),
    StateMachineDefinitionSpec(
        key="dataset_export",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="dataset_export",
        states=("queued", "running", "completed", "failed", "cancelled", "expired"),
        transitions=(
            transition("queued", "running"),
            transition("queued", "cancelled"),
            transition("running", "completed"),
            transition("running", "failed"),
            transition("running", "cancelled"),
            transition("completed", "expired"),
        ),
        terminal_states=("failed", "cancelled", "expired"),
        metadata={"source": "planned_registry_only", "adoption": "future"},
    ),
    StateMachineDefinitionSpec(
        key="webhook_outbox_event",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="webhook_outbox_event",
        states=("queued", "sending", "delivered", "skipped", "failed", "cancelled"),
        transitions=(
            transition("queued", "sending"),
            transition("queued", "skipped"),
            transition("queued", "cancelled"),
            transition("sending", "delivered"),
            transition("sending", "failed"),
            transition("failed", "queued"),
            transition("failed", "cancelled"),
        ),
        terminal_states=("delivered", "skipped", "cancelled"),
        metadata={
            "source": "notifications.models.NotificationStatus",
            "adoption": "future_webhook_channel",
        },
    ),
    StateMachineDefinitionSpec(
        key="provider_polling_request",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="provider_polling_request",
        states=("queued", "running", "completed", "failed", "cancelled", "rate_limited"),
        transitions=(
            transition("queued", "running"),
            transition("queued", "cancelled"),
            transition("running", "completed"),
            transition("running", "failed"),
            transition("running", "rate_limited"),
            transition("rate_limited", "queued"),
            transition("failed", "queued"),
            transition("failed", "cancelled"),
        ),
        terminal_states=("completed", "cancelled"),
        metadata={"source": "planned_registry_only", "adoption": "future"},
    ),
    StateMachineDefinitionSpec(
        key="scheduled_scan_config",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="scheduled_scan_config",
        states=("active", "paused", "disabled", "failed", "archived"),
        transitions=(
            transition("active", "paused"),
            transition("active", "disabled"),
            transition("active", "failed"),
            transition("paused", "active"),
            transition("paused", "disabled"),
            transition("failed", "active"),
            transition("failed", "disabled"),
            transition("disabled", "archived"),
        ),
        terminal_states=("archived",),
        metadata={"source": "planned_registry_only", "adoption": "future"},
    ),
    StateMachineDefinitionSpec(
        key="scheduled_scan_run",
        version=DEFAULT_STATE_MACHINE_VERSION,
        object_type="scheduled_scan_run",
        states=("queued", "running", "completed", "completed_with_warnings", "failed", "cancelled"),
        transitions=(
            transition("queued", "running"),
            transition("queued", "cancelled"),
            transition("running", "completed"),
            transition("running", "completed_with_warnings"),
            transition("running", "failed"),
            transition("running", "cancelled"),
        ),
        terminal_states=("completed", "completed_with_warnings", "failed", "cancelled"),
        metadata={"source": "planned_registry_only", "adoption": "future"},
    ),
)

DEFAULT_STATE_MACHINES_BY_KEY = {
    definition.key: definition for definition in DEFAULT_STATE_MACHINES
}
DEFAULT_STATE_MACHINES_BY_OBJECT_TYPE = {
    definition.object_type: definition for definition in DEFAULT_STATE_MACHINES
}


def get_default_state_machine_by_key(key: str) -> StateMachineDefinitionSpec | None:
    return DEFAULT_STATE_MACHINES_BY_KEY.get(key)


def get_default_state_machine_by_object_type(object_type: str) -> StateMachineDefinitionSpec | None:
    return DEFAULT_STATE_MACHINES_BY_OBJECT_TYPE.get(object_type)


def validate_default_transition(
    object_type: str,
    from_state: str,
    to_state: str,
) -> tuple[bool, str, StateMachineDefinitionSpec | None]:
    definition = get_default_state_machine_by_object_type(object_type)
    if definition is None:
        return False, "State machine is not registered for object type", None
    if from_state not in definition.states:
        return False, "from_state is not allowed for object type", definition
    if to_state not in definition.states:
        return False, "to_state is not allowed for object type", definition
    if from_state in definition.terminal_states:
        return False, "from_state is terminal", definition
    if (from_state, to_state) not in definition.transition_pairs():
        return False, "Transition is not allowed for object type", definition
    return True, "Transition is valid", definition
