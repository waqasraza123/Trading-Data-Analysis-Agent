from app.modules.llm_adapters.schemas import LlmAdapterResponse
from app.modules.reasoning.grounding import check_reasoning_grounding
from app.modules.reasoning.models import ReasoningGroundingStatus, ScenarioType
from app.modules.reasoning.parser import parse_scenario_reasoning_output
from app.modules.reasoning.prompt_builder import build_scenario_reasoning_prompts
from app.modules.reasoning.safety import check_reasoning_safety
from app.tests.unit.reasoning_factories import reasoning_input_snapshot


def valid_output() -> dict[str, object]:
    return {
        "summary": "Scenarios are based only on stored backend facts.",
        "scenarios": [
            {
                "scenarioType": "continuation",
                "scenarioLabel": "Possible follow-through",
                "possibilityLabel": "medium",
                "supportingEvidence": ["Stored evidence remains aligned."],
                "conflictingEvidence": [],
                "outcomeHistory": {"available": False, "summary": "No history supplied."},
                "nextObservations": ["Watch final candles."],
                "suggestedBackendActions": ["evaluate_outcome_after_horizon"],
                "riskNotes": [],
            }
        ],
        "limitations": ["Not a prediction."],
    }


def test_prompt_builder_includes_non_trading_constraints() -> None:
    system_prompt, user_prompt = build_scenario_reasoning_prompts(reasoning_input_snapshot())

    assert "Do not classify or override the signal" in system_prompt
    assert "Do not recommend buying" in system_prompt
    assert "Allowed suggestedBackendActions" in user_prompt


def test_parser_accepts_valid_scenario_json() -> None:
    parsed = parse_scenario_reasoning_output(
        LlmAdapterResponse(
            provider="mock",
            model="mock-scenario-v1",
            output_text="{}",
            output_json=valid_output(),
        )
    )

    assert parsed.fallback_used is False
    assert parsed.scenarios[0].scenario_type == ScenarioType.CONTINUATION


def test_parser_rejects_unknown_scenario_type() -> None:
    payload = valid_output()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    scenarios[0]["scenarioType"] = "prediction"

    parsed = parse_scenario_reasoning_output(
        LlmAdapterResponse(provider="mock", model="mock", output_text="{}", output_json=payload)
    )

    assert parsed.fallback_used is True
    assert parsed.scenarios[0].scenario_type == ScenarioType.INSUFFICIENT_CONTEXT


def test_parser_rejects_trading_backend_actions() -> None:
    payload = valid_output()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    scenarios[0]["suggestedBackendActions"] = ["buy"]

    parsed = parse_scenario_reasoning_output(
        LlmAdapterResponse(provider="mock", model="mock", output_text="{}", output_json=payload)
    )

    assert parsed.fallback_used is True


def test_safety_blocks_direct_trade_instructions() -> None:
    result = check_reasoning_safety("The next action is to buy now.")

    assert result.passed is False
    assert "buy now" in result.blocked_terms


def test_grounding_blocks_invented_news_when_no_news_exists() -> None:
    result = check_reasoning_grounding(
        reasoning_input_snapshot(news_correlations=[]).model_dump(mode="json", by_alias=True),
        valid_output(),
        "A news event may matter.",
    )

    assert result.status == ReasoningGroundingStatus.FAILED
    assert "output mentions news when no news correlations exist" in result.issues


def test_grounding_blocks_invented_numeric_value() -> None:
    result = check_reasoning_grounding(
        reasoning_input_snapshot().model_dump(mode="json", by_alias=True),
        valid_output(),
        "Watch 12345 as a price.",
    )

    assert result.status == ReasoningGroundingStatus.FAILED
    assert any(issue.startswith("invented numeric value") for issue in result.issues)


def test_grounding_blocks_news_causation_language() -> None:
    result = check_reasoning_grounding(
        reasoning_input_snapshot(
            news_correlations=[{"eventTitle": "USD CPI", "eventType": "economic_calendar"}]
        ).model_dump(mode="json", by_alias=True),
        valid_output(),
        "The event caused the move.",
    )

    assert result.status == ReasoningGroundingStatus.FAILED
    assert "output says news caused the move" in result.issues
