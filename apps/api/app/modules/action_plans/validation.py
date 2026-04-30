from dataclasses import dataclass

from app.modules.action_plans.models import ReasoningActionType

TRADING_ACTIONS = {
    "buy",
    "sell",
    "enter_trade",
    "exit_trade",
    "place_order",
    "set_stop_loss",
    "set_take_profit",
    "use_leverage",
    "open_position",
    "close_position",
    "copy_trade",
    "execute_trade",
}
ALLOWED_ACTIONS = {action.value for action in ReasoningActionType}


@dataclass(frozen=True)
class ActionValidationResult:
    accepted: list[ReasoningActionType]
    rejected: list[dict[str, object]]


def validate_backend_actions(actions: list[str]) -> ActionValidationResult:
    accepted: list[ReasoningActionType] = []
    rejected: list[dict[str, object]] = []
    seen: set[str] = set()
    for action in actions:
        normalized = action.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if normalized in TRADING_ACTIONS:
            rejected.append({"actionType": normalized, "reason": "trading_action_rejected"})
            continue
        if normalized not in ALLOWED_ACTIONS:
            rejected.append({"actionType": normalized, "reason": "unknown_action_rejected"})
            continue
        accepted.append(ReasoningActionType(normalized))
    return ActionValidationResult(accepted=accepted, rejected=rejected)
