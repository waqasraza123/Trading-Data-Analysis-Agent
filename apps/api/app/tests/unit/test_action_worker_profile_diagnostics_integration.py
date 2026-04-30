from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.modules.action_plans.models import ReasoningActionType
from app.modules.action_plans.repository import EXECUTABLE_ACTION_TYPES
from app.modules.action_plans.validation import TRADING_ACTIONS
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel, SignalOutcome
from app.modules.profile_diagnostics.calculator import (
    DiagnosticThresholds,
    ProfileDiagnosticCalculator,
)
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendationType,
    DiagnosticLabel,
)
from app.modules.profile_diagnostics.repository import OutcomeSignalRow
from app.modules.profile_diagnostics.service import diagnostic_outcome_from_row
from app.modules.signals.models import SignalBias, SignalClassificationStatus

WORKSPACE_ID = uuid4()
SYMBOL_ID = uuid4()
ANALYSIS_RUN_ID = uuid4()
BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def test_worker_generated_outcome_can_feed_profile_diagnostics() -> None:
    row = OutcomeSignalRow(
        outcome=signal_outcome(OutcomeLabel.CONTINUATION),
        confidence_score=Decimal("0.9000"),
        candidate_strength=Decimal("0.8000"),
    )

    diagnostic_outcome = diagnostic_outcome_from_row(row)
    diagnostics = ProfileDiagnosticCalculator().build_strategy_profile_diagnostics(
        workspace_id=WORKSPACE_ID,
        outcomes=[diagnostic_outcome],
        minimum_sample_size=1,
        thresholds=DiagnosticThresholds(),
    )

    assert diagnostics[0].diagnostic_label == DiagnosticLabel.STRONG_FOLLOW_THROUGH
    assert diagnostics[0].metadata_json["totalOutcomeCount"] == 1
    assert diagnostics[0].metadata_json["directionalEvaluatedOutcomeCount"] == 1


def test_profile_diagnostics_do_not_create_executable_action_types() -> None:
    recommendation_types = {item.value for item in CalibrationRecommendationType}

    assert recommendation_types.isdisjoint(EXECUTABLE_ACTION_TYPES)
    assert recommendation_types.isdisjoint(TRADING_ACTIONS)
    assert "run_profile_diagnostics" not in EXECUTABLE_ACTION_TYPES
    assert "apply_calibration_recommendation" not in EXECUTABLE_ACTION_TYPES


def test_action_worker_keeps_human_review_manual_and_trading_rejected() -> None:
    assert ReasoningActionType.REQUEST_HUMAN_REVIEW.value not in EXECUTABLE_ACTION_TYPES
    assert TRADING_ACTIONS.isdisjoint(EXECUTABLE_ACTION_TYPES)


def signal_outcome(label: OutcomeLabel) -> SignalOutcome:
    return SignalOutcome(
        workspace_id=WORKSPACE_ID,
        analysis_run_id=ANALYSIS_RUN_ID,
        signal_id=uuid4(),
        symbol_id=SYMBOL_ID,
        timeframe="1m",
        strategy_profile_key="default",
        strategy_profile_version="v1",
        pattern_type="breakout",
        bias=SignalBias.BULLISH.value,
        classification_status=SignalClassificationStatus.SIGNAL.value,
        horizon_minutes=15,
        evaluation_status=OutcomeEvaluationStatus.EVALUATED.value,
        reference_time=BASE_TIME,
        reference_price=Decimal("100"),
        future_window_start=BASE_TIME + timedelta(minutes=1),
        future_window_end=BASE_TIME + timedelta(minutes=15),
        future_candle_count=10,
        max_favorable_move=Decimal("1"),
        max_adverse_move=Decimal("0.2"),
        net_move=Decimal("0.5"),
        max_favorable_pips=Decimal("10"),
        max_adverse_pips=Decimal("2"),
        net_pips=Decimal("5"),
        max_favorable_ticks=None,
        max_adverse_ticks=None,
        net_ticks=None,
        direction_followed=True,
        reversal_detected=False,
        outcome_label=label.value,
        movement_quality="test",
        evaluation_version="v1",
        metadata_json={"source": "reasoning_action_worker"},
    )
