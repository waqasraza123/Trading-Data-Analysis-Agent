import json

from app.modules.reasoning.schemas import ScenarioReasoningInputSnapshot

PROMPT_VERSION = "scenario_reasoning_v1"
RESPONSE_SCHEMA_NAME = "scenario_reasoning_output_v1"


def build_scenario_reasoning_prompts(
    input_snapshot: ScenarioReasoningInputSnapshot,
) -> tuple[str, str]:
    system_prompt = (
        "You are explaining deterministic backend market intelligence. "
        "Use only supplied facts. Do not classify or override the signal. "
        "Do not invent prices, indicators, news, outcomes, or evidence. "
        "Do not provide financial advice. Do not recommend buying, selling, entering, "
        "exiting, leverage, or order placement. Do not claim any outcome is guaranteed. "
        "Do not claim news caused a move. Describe plausible scenarios only as possibilities. "
        "If evidence is insufficient, use insufficient_context. "
        "Suggested backend actions must be backend-safe only. "
        "Output strict JSON matching the requested schema."
    )
    user_prompt = (
        "Build grounded next-scenario reasoning from these persisted artifacts only.\n"
        "Allowed scenarioType values: continuation, reversal, consolidation, "
        "volatility_expansion, fakeout_risk, event_driven_volatility, insufficient_context.\n"
        "Allowed possibilityLabel values: low, medium, high, uncertain.\n"
        "Allowed suggestedBackendActions values: evaluate_outcome_after_horizon, run_replay, "
        "run_news_correlation, wait_for_more_final_candles, request_human_review, no_action.\n"
        "Required JSON shape:\n"
        "{"
        '"summary":"string",'
        '"scenarios":[{'
        '"scenarioType":"continuation | reversal | consolidation | volatility_expansion | '
        'fakeout_risk | event_driven_volatility | insufficient_context",'
        '"scenarioLabel":"string",'
        '"possibilityLabel":"low | medium | high | uncertain",'
        '"supportingEvidence":["string"],'
        '"conflictingEvidence":["string"],'
        '"outcomeHistory":{"available":true,"summary":"string"},'
        '"nextObservations":["string"],'
        '"suggestedBackendActions":["evaluate_outcome_after_horizon | run_replay | '
        'run_news_correlation | wait_for_more_final_candles | request_human_review | no_action"],'
        '"riskNotes":["string"]'
        "}],"
        '"limitations":["string"]'
        "}\n"
        "Input artifacts:\n"
        f"{json.dumps(input_snapshot.model_dump(mode='json', by_alias=True), sort_keys=True)}"
    )
    return system_prompt, user_prompt
