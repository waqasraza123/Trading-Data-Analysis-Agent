from __future__ import annotations

import time
from typing import Any

from app.modules.llm_adapters.schemas import LlmAdapterRequest, LlmAdapterResponse


class MockLlmAdapter:
    provider_key = "mock"

    def __init__(self, model_name: str = "mock-scenario-v1") -> None:
        self.model_name = model_name

    async def generate_structured(self, request: LlmAdapterRequest) -> LlmAdapterResponse:
        started = time.perf_counter()
        output_json = build_mock_scenario_output(request.input_json)
        output_text = json_summary(output_json)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return LlmAdapterResponse(
            provider=request.provider,
            model=request.model,
            output_text=output_text,
            output_json=output_json,
            finish_reason="stop",
            tokens_input=rough_token_count(request.system_prompt + request.user_prompt),
            tokens_output=rough_token_count(output_text),
            latency_ms=latency_ms,
        )


def build_mock_scenario_output(input_json: dict[str, Any]) -> dict[str, Any]:
    bias = text_value(input_json.get("bias"), "unclear")
    classification_status = text_value(input_json.get("classificationStatus"), "unknown")
    pattern_type = text_value(input_json.get("patternType"), "stored pattern")
    evidence = list_texts(input_json.get("signalEvidence"), "message", limit=2)
    risk_notes = list_texts(input_json.get("riskNotes"), "message", limit=2)
    outcome_history = input_json.get("outcomeHistory")
    has_history = isinstance(outcome_history, dict) and bool(outcome_history.get("items"))
    scenario_type = "continuation" if bias in {"bullish", "bearish"} else "insufficient_context"
    possibility_label = "medium" if classification_status == "signal" else "uncertain"
    supporting = evidence or ["Stored deterministic artifacts provide limited scenario context."]
    conflicting = risk_notes or ["No specific conflicting evidence was supplied."]
    history_summary = (
        "Stored outcome rows exist for similar backend conditions."
        if has_history
        else "No stored outcome history was supplied for similar backend conditions."
    )
    return {
        "summary": (
            "Scenario reasoning is based only on persisted deterministic artifacts. "
            "It does not change the backend signal classification."
        ),
        "scenarios": [
            {
                "scenarioType": scenario_type,
                "scenarioLabel": f"Possible {bias} follow-through context for {pattern_type}",
                "possibilityLabel": possibility_label,
                "supportingEvidence": supporting,
                "conflictingEvidence": conflicting,
                "outcomeHistory": {
                    "available": has_history,
                    "summary": history_summary,
                },
                "nextObservations": [
                    "Watch whether subsequent final candles confirm or weaken the stored "
                    "pattern context."
                ],
                "suggestedBackendActions": [
                    "evaluate_outcome_after_horizon",
                    "wait_for_more_final_candles",
                ],
                "riskNotes": risk_notes
                or ["Treat this as a scenario to monitor, not an instruction."],
            }
        ],
        "limitations": [
            "Mock provider output is deterministic test output.",
            "Scenarios are possibilities, not predictions or recommendations.",
        ],
    }


def text_value(value: object, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def list_texts(value: object, field: str, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value[:limit]:
        if isinstance(item, dict):
            raw = item.get(field)
            if isinstance(raw, str) and raw.strip():
                output.append(raw.strip())
    return output


def json_summary(payload: dict[str, Any]) -> str:
    summary = payload.get("summary")
    if isinstance(summary, str):
        return summary
    return "Structured scenario reasoning output."


def rough_token_count(value: str) -> int:
    return max(1, len(value.split()))
