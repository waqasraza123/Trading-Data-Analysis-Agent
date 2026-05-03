from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel, SignalOutcome
from app.modules.scenario_outcomes.evaluator import (
    ScenarioNewsContext,
    ScenarioOutcomeEvaluationInput,
    ScenarioOutcomeEvaluator,
)
from app.modules.scenario_outcomes.models import (
    ScenarioOutcomeEvaluationStatus,
    ScenarioOutcomeSupportLabel,
)


def outcome(
    label: str,
    metadata_json: dict[str, object] | None = None,
    movement_quality: str | None = None,
) -> SignalOutcome:
    return SignalOutcome(
        workspace_id=uuid4(),
        analysis_run_id=uuid4(),
        signal_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="1m",
        strategy_profile_key=None,
        strategy_profile_version=None,
        pattern_type=None,
        bias="bullish",
        classification_status="signal",
        horizon_minutes=30,
        evaluation_status=OutcomeEvaluationStatus.EVALUATED,
        reference_time=datetime.now(UTC),
        reference_price=Decimal("100.0000"),
        future_window_start=datetime.now(UTC),
        future_window_end=datetime.now(UTC),
        future_candle_count=5,
        max_favorable_move=Decimal("1.0000"),
        max_adverse_move=Decimal("0.1000"),
        net_move=Decimal("0.8000"),
        max_favorable_pips=None,
        max_adverse_pips=None,
        net_pips=None,
        max_favorable_ticks=None,
        max_adverse_ticks=None,
        net_ticks=None,
        direction_followed=True,
        reversal_detected=False,
        outcome_label=label,
        movement_quality=movement_quality,
        evaluation_version="v1",
        metadata_json=metadata_json or {},
    )


def evaluate(
    scenario_type: str,
    signal_outcome: SignalOutcome | None,
    news_contexts: list[ScenarioNewsContext] | None = None,
) -> tuple[ScenarioOutcomeEvaluationStatus, ScenarioOutcomeSupportLabel]:
    result = ScenarioOutcomeEvaluator().evaluate(
        ScenarioOutcomeEvaluationInput(
            scenario_type=scenario_type,
            scenario_label=scenario_type,
            possibility_label="medium",
            outcome=signal_outcome,
            news_contexts=news_contexts or [],
        ),
        support_threshold=Decimal("0.6000"),
    )
    return result.evaluation_status, result.support_label


def test_continuation_scenario_supported_by_continuation_outcome() -> None:
    status, label = evaluate("continuation", outcome(OutcomeLabel.CONTINUATION))

    assert status == ScenarioOutcomeEvaluationStatus.EVALUATED
    assert label == ScenarioOutcomeSupportLabel.SUPPORTED


def test_reversal_scenario_contradicted_by_continuation_outcome() -> None:
    status, label = evaluate("reversal", outcome(OutcomeLabel.CONTINUATION))

    assert status == ScenarioOutcomeEvaluationStatus.EVALUATED
    assert label == ScenarioOutcomeSupportLabel.CONTRADICTED


def test_consolidation_scenario_supported_by_sideways_outcome() -> None:
    status, label = evaluate("consolidation", outcome(OutcomeLabel.SIDEWAYS_AFTER_SIGNAL))

    assert status == ScenarioOutcomeEvaluationStatus.EVALUATED
    assert label == ScenarioOutcomeSupportLabel.SUPPORTED


def test_missing_outcome_marks_insufficient_data() -> None:
    status, label = evaluate("continuation", None)

    assert status == ScenarioOutcomeEvaluationStatus.INSUFFICIENT_OUTCOME_DATA
    assert label == ScenarioOutcomeSupportLabel.INCONCLUSIVE


def test_event_driven_volatility_requires_news_and_volatility_context() -> None:
    status, label = evaluate(
        "event_driven_volatility",
        outcome(
            OutcomeLabel.PARTIAL_FOLLOW_THROUGH,
            metadata_json={"volatilityReaction": "elevated"},
        ),
        news_contexts=[
            ScenarioNewsContext(correlation_label="possible", volatility_reaction="elevated")
        ],
    )

    assert status == ScenarioOutcomeEvaluationStatus.EVALUATED
    assert label == ScenarioOutcomeSupportLabel.SUPPORTED
