from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.cohort_drift.calculator import CohortDriftCalculator, CohortDriftThresholds
from app.modules.cohort_drift.models import CohortDriftLabel, CohortDriftSeverity
from app.modules.cohort_drift.repository import CohortDriftOutcomeRow
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.signals.models import SignalBias, SignalClassificationStatus


def test_cohort_drift_detects_severe_recent_behavior_change() -> None:
    workspace_id = uuid4()
    symbol_id = uuid4()
    baseline_rows = [
        drift_row(
            symbol_id=symbol_id,
            outcome_label=OutcomeLabel.CONTINUATION.value,
            confidence_score=Decimal("0.80"),
        )
        for _ in range(20)
    ]
    comparison_rows = [
        drift_row(
            symbol_id=symbol_id,
            outcome_label=OutcomeLabel.REVERSAL.value,
            confidence_score=Decimal("0.80"),
        )
        for _ in range(20)
    ]

    results = CohortDriftCalculator().calculate_results(
        workspace_id=workspace_id,
        baseline_rows=baseline_rows,
        comparison_rows=comparison_rows,
        dimensions=["strategy_profile_key", "pattern_type", "symbol_id"],
        horizons_minutes=[15],
        minimum_sample_size=20,
        thresholds=thresholds(),
    )

    assert len(results) == 1
    assert results[0].drift_label == CohortDriftLabel.SEVERE_DRIFT
    assert results[0].severity == CohortDriftSeverity.HIGH
    assert results[0].drift_score == Decimal("1.000000")
    assert results[0].metadata_json["reviewRecommended"] is True


def test_cohort_drift_low_sample_does_not_escalate_to_severe() -> None:
    workspace_id = uuid4()
    symbol_id = uuid4()
    baseline_rows = [
        drift_row(
            symbol_id=symbol_id,
            outcome_label=OutcomeLabel.CONTINUATION.value,
            confidence_score=Decimal("0.90"),
        )
        for _ in range(5)
    ]
    comparison_rows = [
        drift_row(
            symbol_id=symbol_id,
            outcome_label=OutcomeLabel.REVERSAL.value,
            confidence_score=Decimal("0.90"),
        )
        for _ in range(5)
    ]

    results = CohortDriftCalculator().calculate_results(
        workspace_id=workspace_id,
        baseline_rows=baseline_rows,
        comparison_rows=comparison_rows,
        dimensions=["strategy_profile_key", "pattern_type", "symbol_id"],
        horizons_minutes=[15],
        minimum_sample_size=20,
        thresholds=thresholds(),
    )

    assert len(results) == 1
    assert results[0].drift_label == CohortDriftLabel.LOW_SAMPLE
    assert results[0].severity == CohortDriftSeverity.INFO
    assert results[0].drift_score == Decimal("1.000000")
    assert results[0].metadata_json["reviewRecommended"] is False


def drift_row(
    symbol_id: UUID,
    outcome_label: str,
    confidence_score: Decimal,
) -> CohortDriftOutcomeRow:
    return CohortDriftOutcomeRow(
        signal_id=uuid4(),
        horizon_minutes=15,
        reference_time=datetime(2026, 5, 1, tzinfo=UTC),
        strategy_profile_key="breakout_continuation",
        pattern_type="breakout",
        symbol_id=symbol_id,
        timeframe="1m",
        bias=SignalBias.BULLISH.value,
        classification_status=SignalClassificationStatus.SIGNAL.value,
        confidence_score=confidence_score,
        confidence_label="high",
        evaluation_status=OutcomeEvaluationStatus.EVALUATED.value,
        outcome_label=outcome_label,
        market_session_label=None,
        market_regime_label=None,
    )


def thresholds() -> CohortDriftThresholds:
    return CohortDriftThresholds(
        mild_threshold=Decimal("0.10"),
        moderate_threshold=Decimal("0.20"),
        severe_threshold=Decimal("0.35"),
    )
