from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.config import Settings
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.signal_priority.models import SignalPriorityLabel, SignalReviewBucket
from app.modules.signal_priority.repository import SignalPriorityArtifacts
from app.modules.signal_priority.scorer import SignalPriorityScorer
from app.modules.signals.models import (
    Signal,
    SignalBias,
    SignalClassificationStatus,
    SignalConfidenceLabel,
)


def test_priority_score_degrades_missing_optional_context_without_failing() -> None:
    scorer = SignalPriorityScorer(Settings())

    draft = scorer.score(SignalPriorityArtifacts(signal=signal_row(), analysis_run=None))

    assert draft.priority_label == SignalPriorityLabel.LOW
    assert draft.review_bucket == SignalReviewBucket.NEEDS_CONFIRMATION
    assert any(warning["code"] == "missing_context" for warning in draft.warnings_json)


def test_priority_score_marks_stale_data_bucket() -> None:
    scorer = SignalPriorityScorer(Settings())

    draft = scorer.score(
        SignalPriorityArtifacts(
            signal=signal_row(),
            analysis_run=None,
            market_memory=memory_row(freshness_label="stale", data_quality_label="acceptable"),
        )
    )

    assert draft.priority_label == SignalPriorityLabel.STALE
    assert draft.review_bucket == SignalReviewBucket.STALE_OR_DATA_ISSUE
    assert any(penalty["code"] == "stale_data" for penalty in draft.penalties_json)


def test_priority_score_marks_no_signal_as_avoid_bucket() -> None:
    scorer = SignalPriorityScorer(Settings())

    draft = scorer.score(
        SignalPriorityArtifacts(
            signal=signal_row(
                classification_status=SignalClassificationStatus.NO_SIGNAL.value,
                bias=SignalBias.NEUTRAL.value,
                no_signal_reason="insufficient_evidence",
            ),
            analysis_run=None,
            market_memory=memory_row(),
        )
    )

    assert draft.priority_label == SignalPriorityLabel.AVOID
    assert draft.review_bucket == SignalReviewBucket.AVOID_OR_NO_DIRECTIONAL_SIGNAL
    assert any(penalty["code"] == "no_signal_neutral_unclear" for penalty in draft.penalties_json)


def signal_row(
    classification_status: str = SignalClassificationStatus.SIGNAL.value,
    bias: str = SignalBias.BULLISH.value,
    no_signal_reason: str | None = None,
) -> Signal:
    signal_id = uuid4()
    return Signal(
        id=signal_id,
        analysis_run_id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="1h",
        strategy_profile_id=None,
        strategy_profile_key="breakout_continuation",
        strategy_profile_version="v1",
        strategy_profile_snapshot_json=None,
        bias=bias,
        pattern_type="bullish_breakout" if bias == SignalBias.BULLISH.value else None,
        classification_status=classification_status,
        confidence_score=Decimal("0.7200"),
        confidence_label=SignalConfidenceLabel.HIGH.value,
        candidate_strength=Decimal("0.8000"),
        selected_pattern_candidate_id=None,
        pips_moved=None,
        tick_moved=None,
        movement_direction=bias,
        movement_quality="moderate",
        volatility_state="normal",
        trend_state="uptrend",
        range_state="breakout",
        summary="Deterministic signal summary for review.",
        no_signal_reason=no_signal_reason,
        created_at=datetime.now(UTC),
    )


def memory_row(
    freshness_label: str = "fresh",
    data_quality_label: str = "strong",
) -> RollingMarketStateSnapshot:
    return RollingMarketStateSnapshot(
        id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        source_id=None,
        timeframe="1h",
        state_version="v1",
        latest_final_candle_time=datetime.now(UTC),
        latest_analysis_run_id=uuid4(),
        latest_signal_id=uuid4(),
        latest_outcome_id=None,
        data_quality_label=data_quality_label,
        freshness_label=freshness_label,
        trend_state="uptrend",
        volatility_state="normal",
        range_state="breakout",
        market_regime_label="uptrend",
        market_session_label="regular",
        multi_timeframe_label="aligned",
        cross_asset_label="aligned",
        latest_signal_bias=SignalBias.BULLISH.value,
        latest_signal_pattern_type="bullish_breakout",
        latest_signal_confidence_label=SignalConfidenceLabel.HIGH.value,
        context_json={},
        warnings_json=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
