from collections.abc import Callable
from decimal import Decimal

from app.modules.signals.confidence import decimal_value
from app.modules.signals.models import SignalBias, SignalClassificationStatus
from app.modules.signals.types import CandidateEvaluation, ConflictDecision

DIRECTIONAL_BIASES = {"bullish", "bearish"}
CHOP_PATTERNS = {"sideways_range", "low_volatility_chop", "unclear_structure"}
CONTINUATION_PATTERNS = {
    "bullish_breakout",
    "bearish_breakdown",
    "bullish_continuation",
    "bearish_continuation",
}
REVERSAL_PATTERNS = {"bullish_reversal", "bearish_reversal"}


def resolve_conflicts(evaluations: list[CandidateEvaluation]) -> ConflictDecision:
    if not evaluations:
        return ConflictDecision(
            classification_status=SignalClassificationStatus.NO_SIGNAL,
            bias=SignalBias.NEUTRAL,
            selected_evaluation=None,
            no_signal_reason="no_profile_candidates",
            summary=(
                "No signal generated because no profile candidates passed deterministic filters."
            ),
            evidence=(
                classifier_evidence(
                    "classification",
                    "neutral",
                    "No profile candidate passed profile, confidence, and risk filters.",
                ),
            ),
            risk_notes=(
                risk_note(
                    "no_profile_candidates",
                    "No candidate passed deterministic strategy profile filters.",
                    "medium",
                ),
            ),
        )
    ranked = sorted(evaluations, key=lambda item: item.ranking_score, reverse=True)
    best_directional = first_matching(ranked, is_directional)
    best_fakeout = first_matching(ranked, is_fakeout)
    best_chop = first_matching(ranked, is_chop)
    fakeout_decision = fakeout_override(best_directional, best_fakeout)
    if fakeout_decision is not None:
        return fakeout_decision
    chop_decision = chop_override(best_directional, best_chop)
    if chop_decision is not None:
        return chop_decision
    opposing_decision = opposing_directional_conflict(ranked)
    if opposing_decision is not None:
        return opposing_decision
    reversal_decision = reversal_vs_continuation(ranked)
    if reversal_decision is not None:
        return signal_decision(reversal_decision)
    best = ranked[0]
    if is_fakeout(best):
        return no_signal_decision(
            evaluation=best,
            reason="fakeout_risk",
            summary=(
                "No directional signal generated because fakeout evidence met the "
                "protection profile."
            ),
            message="Fakeout protection profile produced the strongest eligible candidate.",
        )
    if is_chop(best):
        return no_signal_decision(
            evaluation=best,
            reason="chop_or_sideways_market",
            summary=(
                "No directional signal generated because market conditions are choppy or sideways."
            ),
            message="Range/chop avoidance profile produced the strongest eligible candidate.",
        )
    if is_directional(best):
        return signal_decision(best)
    return ConflictDecision(
        classification_status=SignalClassificationStatus.UNCLEAR,
        bias=SignalBias.UNCLEAR,
        selected_evaluation=best,
        no_signal_reason="insufficient_evidence",
        summary="No clear deterministic signal generated from eligible candidates.",
        evidence=(
            classifier_evidence(
                "classification",
                "neutral",
                "Eligible candidates did not produce a clear directional classification.",
            ),
        ),
        risk_notes=(
            risk_note(
                "insufficient_evidence",
                "Eligible candidates did not produce a clear directional classification.",
                "medium",
            ),
        ),
    )


def fakeout_override(
    best_directional: CandidateEvaluation | None,
    best_fakeout: CandidateEvaluation | None,
) -> ConflictDecision | None:
    if best_fakeout is None:
        return None
    if best_directional is None:
        return no_signal_decision(
            evaluation=best_fakeout,
            reason="fakeout_risk",
            summary="No directional signal generated because fakeout evidence was strongest.",
            message=(
                "Fakeout candidate passed the fakeout protection profile without a "
                "stronger directional candidate."
            ),
        )
    margin = profile_decimal(best_directional, "fakeout_override_margin", Decimal("0.1200"))
    if best_directional.candidate.strength_score - best_fakeout.candidate.strength_score <= margin:
        return no_signal_decision(
            evaluation=best_fakeout,
            reason="fakeout_risk",
            summary=(
                "No directional signal generated because fakeout risk was within "
                "the configured conflict margin."
            ),
            message=(
                "Fakeout candidate strength was close enough to the directional "
                "candidate to override classification."
            ),
        )
    return None


def chop_override(
    best_directional: CandidateEvaluation | None,
    best_chop: CandidateEvaluation | None,
) -> ConflictDecision | None:
    if best_chop is None:
        return None
    if best_directional is None:
        return no_signal_decision(
            evaluation=best_chop,
            reason="chop_or_sideways_market",
            summary=(
                "No directional signal generated because chop or sideways evidence was strongest."
            ),
            message=(
                "Range/chop candidate passed the avoidance profile without a stronger "
                "directional candidate."
            ),
        )
    margin = profile_decimal(best_directional, "chop_override_margin", Decimal("0.1000"))
    if best_directional.candidate.strength_score - best_chop.candidate.strength_score <= margin:
        return no_signal_decision(
            evaluation=best_chop,
            reason="chop_or_sideways_market",
            summary=(
                "No directional signal generated because chop or sideways evidence "
                "was within the configured conflict margin."
            ),
            message=(
                "Range/chop candidate strength was close enough to the directional "
                "candidate to block classification."
            ),
        )
    return None


def opposing_directional_conflict(
    ranked: list[CandidateEvaluation],
) -> ConflictDecision | None:
    best_bullish = first_matching(ranked, lambda item: item.candidate.bias == "bullish")
    best_bearish = first_matching(ranked, lambda item: item.candidate.bias == "bearish")
    if best_bullish is None or best_bearish is None:
        return None
    stronger = (
        best_bullish if best_bullish.ranking_score >= best_bearish.ranking_score else best_bearish
    )
    weaker = best_bearish if stronger is best_bullish else best_bullish
    margin = profile_decimal(stronger, "opposing_bias_conflict_margin", Decimal("0.0800"))
    if stronger.ranking_score - weaker.ranking_score <= margin:
        return ConflictDecision(
            classification_status=SignalClassificationStatus.UNCLEAR,
            bias=SignalBias.UNCLEAR,
            selected_evaluation=stronger,
            no_signal_reason="conflicting_directional_candidates",
            summary=(
                "No directional signal generated because bullish and bearish "
                "candidates were too close."
            ),
            evidence=(
                classifier_evidence(
                    "conflict_resolution",
                    "neutral",
                    (
                        "Top bullish and bearish candidates were within the "
                        "configured conflict margin."
                    ),
                ),
            ),
            risk_notes=(
                risk_note(
                    "conflicting_directional_candidates",
                    (
                        "Bullish and bearish candidates were too close for "
                        "deterministic classification."
                    ),
                    "high",
                ),
            ),
        )
    return None


def reversal_vs_continuation(ranked: list[CandidateEvaluation]) -> CandidateEvaluation | None:
    best_reversal = first_matching(ranked, is_reversal)
    best_continuation = first_matching(ranked, is_continuation)
    if best_reversal is None or best_continuation is None:
        return None
    if ranked[0] is not best_reversal:
        return None
    margin = profile_decimal(best_reversal, "reversal_required_margin", Decimal("0.0800"))
    strength_margin_met = (
        best_reversal.candidate.strength_score - best_continuation.candidate.strength_score
        >= margin
    )
    confidence_margin_met = (
        best_reversal.confidence.confidence_score - best_continuation.confidence.confidence_score
        >= margin
    )
    if strength_margin_met and confidence_margin_met:
        return best_reversal
    return best_continuation


def signal_decision(evaluation: CandidateEvaluation) -> ConflictDecision:
    bias = SignalBias.BULLISH if evaluation.candidate.bias == "bullish" else SignalBias.BEARISH
    return ConflictDecision(
        classification_status=SignalClassificationStatus.SIGNAL,
        bias=bias,
        selected_evaluation=evaluation,
        no_signal_reason=None,
        summary=(
            f"{bias.value.capitalize()} {evaluation.candidate.pattern_type} classified by "
            f"{evaluation.profile.key} profile."
        ),
        evidence=(
            classifier_evidence(
                "classification",
                f"supports_{bias.value}",
                (
                    f"Selected {evaluation.candidate.pattern_type} candidate because it passed "
                    f"{evaluation.profile.key} thresholds."
                ),
            ),
        ),
        risk_notes=(),
    )


def no_signal_decision(
    evaluation: CandidateEvaluation,
    reason: str,
    summary: str,
    message: str,
) -> ConflictDecision:
    return ConflictDecision(
        classification_status=SignalClassificationStatus.NO_SIGNAL,
        bias=SignalBias.NEUTRAL,
        selected_evaluation=evaluation,
        no_signal_reason=reason,
        summary=summary,
        evidence=(classifier_evidence("conflict_resolution", "neutral", message),),
        risk_notes=(risk_note(reason, message, "high"),),
    )


def first_matching(
    evaluations: list[CandidateEvaluation],
    predicate: Callable[[CandidateEvaluation], bool],
) -> CandidateEvaluation | None:
    for evaluation in evaluations:
        if predicate(evaluation):
            return evaluation
    return None


def is_directional(evaluation: CandidateEvaluation) -> bool:
    return evaluation.candidate.bias in DIRECTIONAL_BIASES


def is_fakeout(evaluation: CandidateEvaluation) -> bool:
    return (
        evaluation.candidate.pattern_type == "fakeout"
        or evaluation.profile.key == "fakeout_protection"
    )


def is_chop(evaluation: CandidateEvaluation) -> bool:
    return (
        evaluation.candidate.pattern_type in CHOP_PATTERNS
        or evaluation.profile.key == "range_chop_avoidance"
    )


def is_continuation(evaluation: CandidateEvaluation) -> bool:
    return evaluation.candidate.pattern_type in CONTINUATION_PATTERNS


def is_reversal(evaluation: CandidateEvaluation) -> bool:
    return evaluation.candidate.pattern_type in REVERSAL_PATTERNS


def profile_decimal(
    evaluation: CandidateEvaluation,
    key: str,
    default: Decimal,
) -> Decimal:
    value = decimal_value(evaluation.profile.risk_filters_json.get(key))
    return value if value is not None else default


def classifier_evidence(
    evidence_type: str,
    direction: str,
    message: str,
) -> dict[str, object]:
    return {
        "evidence_type": evidence_type,
        "direction": direction,
        "message": message,
        "weight": "0.00000",
        "metadata": {},
    }


def risk_note(code: str, message: str, severity: str) -> dict[str, object]:
    return {"code": code, "message": message, "severity": severity, "metadata": {}}
