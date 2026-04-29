from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.explanations.models import ExplanationSafetyStatus, ExplanationType
from app.modules.explanations.safety import check_explanation_safety
from app.modules.explanations.service import build_explanation_model
from app.modules.explanations.templates import (
    FALLBACK_EXPLANATION,
    NO_SIGNAL_REASON_MESSAGES,
    ExplanationDraft,
    build_confidence_summary,
    build_evidence_summary,
    build_explanation_draft,
    build_market_behavior,
    build_no_signal_reason_message,
    build_risk_summary,
)
from app.modules.signals.models import (
    Signal,
    SignalBias,
    SignalClassificationStatus,
    SignalConfidenceComponent,
    SignalConfidenceLabel,
    SignalEvidence,
    SignalRiskNote,
)


def test_bullish_signal_explanation_uses_market_analysis_language() -> None:
    signal = signal_row(SignalClassificationStatus.SIGNAL, SignalBias.BULLISH)

    draft = build_explanation_draft(
        signal=signal,
        confidence_components=[component("pattern_strength", "0.9000")],
        evidence=[evidence_row("Pattern evidence breakout passed.", "supports_bullish")],
        risk_notes=[risk_note("volatility_expansion", "Volatility expansion was present.")],
        feature_snapshot=None,
        indicator_snapshot=None,
    )

    assert draft.explanation_type == ExplanationType.DETERMINISTIC_SIGNAL
    assert draft.short_summary == (
        "The signal was classified as bullish by the breakout_continuation profile."
    )
    assert "buy now" not in draft.full_text.lower()
    assert "trade instruction" in draft.full_text


def test_bearish_signal_explanation_uses_market_analysis_language() -> None:
    signal = signal_row(
        SignalClassificationStatus.SIGNAL,
        SignalBias.BEARISH,
        pattern_type="bearish_breakdown",
        movement_direction="bearish",
    )

    draft = build_explanation_draft(
        signal=signal,
        confidence_components=[component("pattern_strength", "0.8800")],
        evidence=[evidence_row("Pattern evidence breakdown passed.", "supports_bearish")],
        risk_notes=[],
        feature_snapshot=None,
        indicator_snapshot=None,
    )

    assert "classified as bearish" in draft.short_summary
    assert "Pattern type was bearish_breakdown." in draft.market_behavior
    assert "sell now" not in draft.full_text.lower()


def test_no_signal_explanation_maps_reason() -> None:
    signal = signal_row(
        SignalClassificationStatus.NO_SIGNAL,
        SignalBias.NEUTRAL,
        no_signal_reason="chop_or_sideways_market",
    )

    draft = build_explanation_draft(
        signal=signal,
        confidence_components=[],
        evidence=[],
        risk_notes=[],
        feature_snapshot=None,
        indicator_snapshot=None,
    )

    assert draft.explanation_type == ExplanationType.DETERMINISTIC_NO_SIGNAL
    assert draft.no_signal_summary == NO_SIGNAL_REASON_MESSAGES["chop_or_sideways_market"]


def test_unclear_explanation_focuses_on_conflict() -> None:
    signal = signal_row(
        SignalClassificationStatus.UNCLEAR,
        SignalBias.UNCLEAR,
        no_signal_reason="conflicting_directional_candidates",
    )

    draft = build_explanation_draft(
        signal=signal,
        confidence_components=[],
        evidence=[],
        risk_notes=[],
        feature_snapshot=None,
        indicator_snapshot=None,
    )

    assert "unclear" in draft.short_summary
    assert "opposing directional candidates" in str(draft.no_signal_summary)


def test_insufficient_evidence_explanation_maps_reason() -> None:
    signal = signal_row(
        SignalClassificationStatus.INSUFFICIENT_EVIDENCE,
        SignalBias.NEUTRAL,
        no_signal_reason="insufficient_evidence",
    )

    draft = build_explanation_draft(
        signal=signal,
        confidence_components=[],
        evidence=[],
        risk_notes=[],
        feature_snapshot=None,
        indicator_snapshot=None,
    )

    assert draft.short_summary == NO_SIGNAL_REASON_MESSAGES["insufficient_evidence"]
    assert draft.no_signal_summary == NO_SIGNAL_REASON_MESSAGES["insufficient_evidence"]


@pytest.mark.parametrize("reason", sorted(NO_SIGNAL_REASON_MESSAGES))
def test_no_signal_reason_message_mapping(reason: str) -> None:
    assert build_no_signal_reason_message(reason) == NO_SIGNAL_REASON_MESSAGES[reason]


def test_unknown_no_signal_reason_message_mapping_is_safe() -> None:
    assert build_no_signal_reason_message("unknown") == (
        "No signal was generated because deterministic classification did not find enough "
        "clean evidence."
    )


def test_confidence_summary_lists_score_label_components_and_data_quality() -> None:
    signal = signal_row(SignalClassificationStatus.SIGNAL, SignalBias.BULLISH)
    summary = build_confidence_summary(
        signal,
        [
            component("pattern_strength", "0.9500", weighted_score="0.45000"),
            component("data_quality", "0.7000", weighted_score="0.07000"),
            component("indicator_support", "0.3000", weighted_score="0.03000"),
        ],
    )

    assert "Confidence score was 0.72 with label medium." in summary
    assert "Strongest components were pattern_strength (0.95), data_quality (0.7)." in summary
    assert "Weakest components were indicator_support (0.3), data_quality (0.7)." in summary
    assert "Data quality impact:" in summary


def test_evidence_summary_uses_persisted_evidence_only() -> None:
    summary = build_evidence_summary(
        [evidence_row("Pattern evidence range break passed.", "supports_bullish")]
    )

    assert "Pattern evidence range break passed." in summary
    assert "supports_bullish" in summary


def test_risk_summary_uses_generic_line_when_missing() -> None:
    assert build_risk_summary([]) == (
        "No additional deterministic risk notes were attached to this signal."
    )


def test_safety_checker_blocks_unsafe_phrases() -> None:
    result = check_explanation_safety("This is guaranteed profit and a sure win.")

    assert not result.passed
    assert result.blocked_terms == ["guaranteed", "sure win", "guaranteed profit"]


@pytest.mark.parametrize(
    "phrase",
    [
        "buy now",
        "sell now",
        "guaranteed",
        "risk-free",
        "sure win",
        "must enter",
        "cannot lose",
        "use leverage",
        "take this trade",
        "enter now",
        "exit now",
    ],
)
def test_safety_checker_blocks_required_unsafe_phrases(phrase: str) -> None:
    result = check_explanation_safety(f"Unsafe phrase: {phrase}.")

    assert not result.passed
    assert phrase in result.blocked_terms


def test_safety_checker_allows_negative_financial_advice_disclaimer() -> None:
    result = check_explanation_safety("This is not financial advice.")

    assert result.passed


def test_fallback_explanation_when_blocked() -> None:
    signal = signal_row(SignalClassificationStatus.SIGNAL, SignalBias.BULLISH)
    draft = ExplanationDraft(
        template_version="deterministic_v1",
        explanation_type=ExplanationType.DETERMINISTIC_SIGNAL,
        short_summary="Unsafe",
        market_behavior="Unsafe",
        evidence_summary="Unsafe",
        confidence_summary="Unsafe",
        risk_summary="Unsafe",
        no_signal_summary=None,
        full_text="buy now",
        source_snapshot_json={"signal": {"id": str(signal.id)}},
    )

    explanation = build_explanation_model(signal, draft)

    assert explanation.safety_status == ExplanationSafetyStatus.BLOCKED
    assert explanation.full_text == FALLBACK_EXPLANATION
    assert explanation.blocked_terms_json == ["buy now"]


def test_market_behavior_does_not_invent_missing_pips_or_ticks() -> None:
    signal = signal_row(SignalClassificationStatus.SIGNAL, SignalBias.BULLISH)
    signal.pips_moved = None
    signal.tick_moved = None

    summary = build_market_behavior(signal)

    assert "pips" not in summary
    assert "ticks" not in summary


def test_missing_evidence_is_handled_safely() -> None:
    assert build_evidence_summary([]) == (
        "No persisted signal evidence rows were attached to this signal."
    )


def test_missing_confidence_components_are_handled_safely() -> None:
    signal = signal_row(SignalClassificationStatus.SIGNAL, SignalBias.BULLISH)

    summary = build_confidence_summary(signal, [])

    assert "No persisted confidence components were attached to this signal." in summary


def signal_row(
    classification_status: SignalClassificationStatus,
    bias: SignalBias,
    pattern_type: str | None = "bullish_breakout",
    movement_direction: str | None = "bullish",
    no_signal_reason: str | None = None,
) -> Signal:
    return Signal(
        id=uuid4(),
        analysis_run_id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="M5",
        strategy_profile_id=uuid4(),
        strategy_profile_key="breakout_continuation",
        strategy_profile_version="v1",
        strategy_profile_snapshot_json={
            "key": "breakout_continuation",
            "version": "v1",
        },
        bias=bias.value,
        pattern_type=pattern_type,
        classification_status=classification_status.value,
        confidence_score=Decimal("0.7200"),
        confidence_label=SignalConfidenceLabel.MEDIUM.value,
        candidate_strength=Decimal("0.8000"),
        selected_pattern_candidate_id=uuid4(),
        pips_moved=None,
        tick_moved=None,
        movement_direction=movement_direction,
        movement_quality="efficient",
        volatility_state="expanding",
        trend_state="short_term_uptrend",
        range_state="above_previous_range",
        summary="Deterministic test signal.",
        no_signal_reason=no_signal_reason,
    )


def component(
    name: str,
    score: str,
    weighted_score: str = "0.10000",
) -> SignalConfidenceComponent:
    return SignalConfidenceComponent(
        id=uuid4(),
        signal_id=uuid4(),
        component_name=name,
        component_score=Decimal(score),
        component_weight=Decimal("0.1000"),
        weighted_score=Decimal(weighted_score),
        reason=f"{name} reason from persisted classifier.",
    )


def evidence_row(message: str, direction: str) -> SignalEvidence:
    return SignalEvidence(
        id=uuid4(),
        signal_id=uuid4(),
        evidence_type="classification",
        direction=direction,
        message=message,
        numeric_value=None,
        weight=Decimal("0.50000"),
        metadata_json={},
    )


def risk_note(code: str, message: str) -> SignalRiskNote:
    return SignalRiskNote(
        id=uuid4(),
        signal_id=uuid4(),
        code=code,
        message=message,
        severity="medium",
        metadata_json={},
    )
