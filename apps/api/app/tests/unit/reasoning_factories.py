from datetime import UTC, datetime
from uuid import uuid4

from app.modules.reasoning.schemas import ScenarioReasoningInputSnapshot


def reasoning_input_snapshot(
    news_correlations: list[dict[str, object]] | None = None,
    outcome_items: list[dict[str, object]] | None = None,
) -> ScenarioReasoningInputSnapshot:
    return ScenarioReasoningInputSnapshot(
        signal_id=uuid4(),
        analysis_run_id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        symbol="EURUSD",
        timeframe="1m",
        analysis_window={
            "startTime": datetime(2026, 4, 30, 10, 0, tzinfo=UTC).isoformat(),
            "endTime": datetime(2026, 4, 30, 10, 15, tzinfo=UTC).isoformat(),
        },
        classification_status="signal",
        bias="bullish",
        pattern_type="breakout",
        strategy_profile_key="default",
        strategy_profile_version="v1",
        confidence_score="0.8",
        confidence_label="high",
        signal_summary="Stored signal summary.",
        no_signal_reason=None,
        confidence_components=[],
        signal_evidence=[{"message": "Stored evidence remains aligned."}],
        risk_notes=[],
        deterministic_explanation=None,
        news_correlations=news_correlations or [],
        latest_signal_outcomes=[],
        outcome_history={
            "filters": {},
            "items": outcome_items or [],
            "totalMatchingOutcomeCount": 0,
            "truncatedPerHorizonLimit": 80,
        },
        feature_summary=None,
        indicator_summary=None,
        replay_metadata=None,
        screenshot_decision_metadata=None,
        truncation={},
    )
