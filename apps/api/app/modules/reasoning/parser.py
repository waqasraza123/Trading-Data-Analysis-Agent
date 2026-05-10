from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.modules.llm_adapters.schemas import LlmAdapterResponse
from app.modules.reasoning.models import ScenarioPossibilityLabel, ScenarioType
from app.modules.reasoning.schemas import ParsedScenarioReasoning, ScenarioOutput

ALLOWED_BACKEND_ACTIONS = {
    "evaluate_outcome_after_horizon",
    "run_replay",
    "run_news_correlation",
    "wait_for_more_final_candles",
    "request_human_review",
    "no_action",
}
TRADING_ACTION_TERMS = {
    "buy",
    "sell",
    "enter",
    "exit",
    "take_profit",
    "stop_loss",
    "leverage",
    "place_order",
    "execute_trade",
    "long",
    "short",
}


def parse_scenario_reasoning_output(
    adapter_response: LlmAdapterResponse,
) -> ParsedScenarioReasoning:
    payload = adapter_response.output_json or parse_text_json(adapter_response.output_text)
    if payload is None:
        return fallback_parsed("model_output_was_not_json")
    try:
        return parse_payload(payload)
    except (TypeError, ValueError, ValidationError) as exc:
        return fallback_parsed(str(exc))


def parse_payload(payload: dict[str, Any]) -> ParsedScenarioReasoning:
    summary = string_value(payload.get("summary"), "Scenario reasoning fallback was used.")
    raw_scenarios = payload.get("scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise ValueError("scenarios must contain at least one item")
    scenarios: list[ScenarioOutput] = []
    for item in raw_scenarios:
        if not isinstance(item, dict):
            raise ValueError("scenario item must be an object")
        scenario_type = scenario_enum(item.get("scenarioType"))
        possibility_label = possibility_enum(item.get("possibilityLabel"))
        actions = normalize_backend_actions(item.get("suggestedBackendActions"))
        scenarios.append(
            ScenarioOutput(
                scenario_type=scenario_type,
                scenario_label=string_value(item.get("scenarioLabel"), "Scenario to monitor"),
                possibility_label=possibility_label,
                supporting_evidence=string_list(item.get("supportingEvidence")),
                conflicting_evidence=string_list(item.get("conflictingEvidence")),
                outcome_history=object_dict(item.get("outcomeHistory")),
                next_observations=string_list(item.get("nextObservations")),
                suggested_backend_actions=actions,
                risk_notes=string_list(item.get("riskNotes")),
            )
        )
    return ParsedScenarioReasoning(
        summary=summary,
        scenarios=scenarios,
        limitations=string_list(payload.get("limitations")),
    )


def fallback_parsed(reason: str) -> ParsedScenarioReasoning:
    return ParsedScenarioReasoning(
        summary=(
            "The LLM output could not be safely parsed. Review deterministic artifacts directly."
        ),
        scenarios=[
            ScenarioOutput(
                scenario_type=ScenarioType.INSUFFICIENT_CONTEXT,
                scenario_label="Insufficient grounded scenario context",
                possibility_label=ScenarioPossibilityLabel.UNCERTAIN,
                supporting_evidence=[],
                conflicting_evidence=[],
                outcome_history={"available": False, "summary": "No parsed outcome history."},
                next_observations=["Review deterministic signal evidence and risk notes directly."],
                suggested_backend_actions=["request_human_review"],
                risk_notes=["Parser fallback was used."],
            )
        ],
        limitations=[reason],
        fallback_used=True,
        error_message=reason,
    )


def parse_text_json(output_text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def scenario_enum(value: object) -> ScenarioType:
    if not isinstance(value, str):
        raise ValueError("scenarioType must be a string")
    try:
        return ScenarioType(value)
    except ValueError as exc:
        raise ValueError(f"unknown scenarioType: {value}") from exc


def possibility_enum(value: object) -> ScenarioPossibilityLabel:
    if not isinstance(value, str):
        raise ValueError("possibilityLabel must be a string")
    try:
        return ScenarioPossibilityLabel(value)
    except ValueError as exc:
        raise ValueError(f"unknown possibilityLabel: {value}") from exc


def normalize_backend_actions(value: object) -> list[str]:
    actions = string_list(value)
    for action in actions:
        normalized = action.strip().lower()
        if normalized in TRADING_ACTION_TERMS:
            raise ValueError(f"trading backend action is not allowed: {action}")
        if normalized not in ALLOWED_BACKEND_ACTIONS:
            raise ValueError(f"unknown backend action: {action}")
    return actions or ["request_human_review"]


def string_value(value: object, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            output.append(item.strip())
    return output


def object_dict(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return None
