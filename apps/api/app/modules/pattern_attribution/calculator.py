from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.pattern_attribution.models import PatternAttributionLabel
from app.modules.signals.models import SignalClassificationStatus

BLOCKER_PATTERN_TYPES = {"fakeout", "sideways_range", "low_volatility_chop", "unclear_structure"}
BLOCKER_REASON_CODES = {"fakeout_risk", "chop_or_sideways_market"}


@dataclass(frozen=True)
class AttributionThresholds:
    high_rejection_rate: Decimal = Decimal("0.50")
    high_reversal_rate: Decimal = Decimal("0.35")


@dataclass(frozen=True)
class CandidateAttributionObservation:
    workspace_id: UUID
    candidate_id: UUID
    signal_id: UUID | None
    pattern_type: str
    strategy_profile_key: str | None
    symbol_id: UUID
    timeframe: str
    horizon_minutes: int
    strength_score: Decimal
    selected_confidence: Decimal | None
    behavior: str
    outcome_label: str | None
    evaluation_status: str | None
    missing_outcome: bool


@dataclass(frozen=True, kw_only=True)
class PatternAttributionAggregate:
    workspace_id: UUID
    pattern_type: str
    strategy_profile_key: str | None
    symbol_id: UUID | None
    timeframe: str | None
    horizon_minutes: int | None
    candidate_count: int
    selected_count: int
    rejected_count: int
    blocked_count: int
    average_strength_score: Decimal | None
    average_selected_confidence: Decimal | None
    continuation_count: int
    partial_follow_through_count: int
    no_follow_through_count: int
    reversal_count: int
    insufficient_data_count: int
    continuation_rate: Decimal | None
    reversal_rate: Decimal | None
    no_follow_through_rate: Decimal | None
    attribution_label: PatternAttributionLabel
    diagnostic_summary: str
    metadata_json: dict[str, object] = field(default_factory=dict)


class PatternAttributionCalculator:
    def build_results(
        self,
        observations: list[CandidateAttributionObservation],
        minimum_sample_size: int,
        thresholds: AttributionThresholds,
    ) -> list[PatternAttributionAggregate]:
        grouped: dict[
            tuple[str, str | None, UUID | None, str | None, int | None],
            list[CandidateAttributionObservation],
        ] = {}
        for observation in observations:
            keys = [
                (
                    observation.pattern_type,
                    None,
                    None,
                    None,
                    observation.horizon_minutes,
                ),
                (
                    observation.pattern_type,
                    observation.strategy_profile_key,
                    observation.symbol_id,
                    observation.timeframe,
                    observation.horizon_minutes,
                ),
            ]
            for key in keys:
                grouped.setdefault(key, []).append(observation)
        return [
            calculate_group(
                workspace_id=rows[0].workspace_id,
                key=key,
                observations=rows,
                minimum_sample_size=minimum_sample_size,
                thresholds=thresholds,
            )
            for key, rows in sorted(grouped.items(), key=lambda item: sort_key(item[0]))
        ]


def calculate_group(
    workspace_id: UUID,
    key: tuple[str, str | None, UUID | None, str | None, int | None],
    observations: list[CandidateAttributionObservation],
    minimum_sample_size: int,
    thresholds: AttributionThresholds,
) -> PatternAttributionAggregate:
    pattern_type, strategy_profile_key, symbol_id, timeframe, horizon_minutes = key
    selected_count = count_behavior(observations, "selected")
    rejected_count = count_behavior(observations, "rejected")
    blocked_count = count_behavior(observations, "blocked")
    continuation_count = count_outcome(observations, OutcomeLabel.CONTINUATION.value)
    partial_count = count_outcome(observations, OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value)
    reversal_count = count_outcome(observations, OutcomeLabel.REVERSAL.value)
    no_follow_count = no_follow_through_count(observations)
    insufficient_count = count_outcome(observations, OutcomeLabel.INSUFFICIENT_DATA.value)
    candidate_count = len(observations)
    outcome_count = continuation_count + partial_count + no_follow_count + reversal_count
    continuation_rate = optional_rate(continuation_count + partial_count, outcome_count)
    reversal_rate = optional_rate(reversal_count, outcome_count)
    no_follow_rate = optional_rate(no_follow_count, outcome_count)
    rejection_rate = rate(rejected_count, candidate_count)
    selected_rate = rate(selected_count, candidate_count)
    blocked_rate = rate(blocked_count, candidate_count)
    label = attribution_label(
        candidate_count=candidate_count,
        outcome_count=outcome_count,
        selected_count=selected_count,
        blocked_count=blocked_count,
        rejection_rate=rejection_rate,
        selected_rate=selected_rate,
        blocked_rate=blocked_rate,
        continuation_rate=continuation_rate,
        reversal_rate=reversal_rate,
        no_follow_through_rate=no_follow_rate,
        minimum_sample_size=minimum_sample_size,
        thresholds=thresholds,
    )
    missing_outcome_count = sum(1 for observation in observations if observation.missing_outcome)
    metadata_json: dict[str, object] = {
        "candidateObservationCount": candidate_count,
        "outcomeObservationCount": outcome_count,
        "missingOutcomeCount": missing_outcome_count,
        "selectedRate": decimal_to_string(selected_rate),
        "rejectedRate": decimal_to_string(rejection_rate),
        "blockedRate": decimal_to_string(blocked_rate),
        "behaviorCounts": {
            "selected": selected_count,
            "rejected": rejected_count,
            "blocked": blocked_count,
            "observed": count_behavior(observations, "observed"),
        },
        "minimumSampleSize": minimum_sample_size,
        "thresholds": {
            "highRejectionRate": str(thresholds.high_rejection_rate),
            "highReversalRate": str(thresholds.high_reversal_rate),
        },
    }
    return PatternAttributionAggregate(
        workspace_id=workspace_id,
        pattern_type=pattern_type,
        strategy_profile_key=strategy_profile_key,
        symbol_id=symbol_id,
        timeframe=timeframe,
        horizon_minutes=horizon_minutes,
        candidate_count=candidate_count,
        selected_count=selected_count,
        rejected_count=rejected_count,
        blocked_count=blocked_count,
        average_strength_score=average_decimal(
            [observation.strength_score for observation in observations]
        ),
        average_selected_confidence=average_optional_decimal(
            [observation.selected_confidence for observation in observations]
        ),
        continuation_count=continuation_count,
        partial_follow_through_count=partial_count,
        no_follow_through_count=no_follow_count,
        reversal_count=reversal_count,
        insufficient_data_count=insufficient_count,
        continuation_rate=continuation_rate,
        reversal_rate=reversal_rate,
        no_follow_through_rate=no_follow_rate,
        attribution_label=label,
        diagnostic_summary=diagnostic_summary(pattern_type, horizon_minutes, label),
        metadata_json=metadata_json,
    )


def attribution_label(
    candidate_count: int,
    outcome_count: int,
    selected_count: int,
    blocked_count: int,
    rejection_rate: Decimal,
    selected_rate: Decimal,
    blocked_rate: Decimal,
    continuation_rate: Decimal | None,
    reversal_rate: Decimal | None,
    no_follow_through_rate: Decimal | None,
    minimum_sample_size: int,
    thresholds: AttributionThresholds,
) -> PatternAttributionLabel:
    if candidate_count < minimum_sample_size:
        return PatternAttributionLabel.LOW_SAMPLE
    if rejection_rate >= thresholds.high_rejection_rate:
        return PatternAttributionLabel.OFTEN_REJECTED
    if outcome_count == 0:
        return PatternAttributionLabel.INSUFFICIENT_DATA
    if reversal_rate is not None and reversal_rate >= thresholds.high_reversal_rate:
        return PatternAttributionLabel.REVERSAL_PRONE
    if (
        blocked_count > 0
        and blocked_rate >= selected_rate
        and no_follow_through_rate is not None
        and no_follow_through_rate >= max_rate(continuation_rate, reversal_rate)
    ):
        return PatternAttributionLabel.BLOCKING_EFFECTIVE
    if (
        selected_count > 0
        and selected_rate >= blocked_rate
        and continuation_rate is not None
        and continuation_rate > max_rate(reversal_rate, no_follow_through_rate)
    ):
        return PatternAttributionLabel.STRONG_SELECTED_BEHAVIOR
    return PatternAttributionLabel.MIXED


def diagnostic_summary(
    pattern_type: str,
    horizon_minutes: int | None,
    label: PatternAttributionLabel,
) -> str:
    horizon_text = f"{horizon_minutes} minutes" if horizon_minutes is not None else "all horizons"
    summaries = {
        PatternAttributionLabel.STRONG_SELECTED_BEHAVIOR: (
            f"{pattern_type} shows strong selected-candidate contribution at {horizon_text}."
        ),
        PatternAttributionLabel.OFTEN_REJECTED: (
            f"{pattern_type} candidates are frequently rejected at {horizon_text}."
        ),
        PatternAttributionLabel.REVERSAL_PRONE: (
            f"{pattern_type} selected candidates show elevated reversal observations "
            f"at {horizon_text}."
        ),
        PatternAttributionLabel.BLOCKING_EFFECTIVE: (
            f"{pattern_type} blocker candidates frequently prevent directional classification "
            f"at {horizon_text}."
        ),
        PatternAttributionLabel.MIXED: (
            f"{pattern_type} has mixed candidate attribution behavior at {horizon_text}."
        ),
        PatternAttributionLabel.LOW_SAMPLE: (
            f"{pattern_type} has too few candidate observations for stable attribution "
            f"at {horizon_text}."
        ),
        PatternAttributionLabel.INSUFFICIENT_DATA: (
            f"{pattern_type} lacks enough observed outcome coverage at {horizon_text}."
        ),
    }
    return summaries[label]


def candidate_behavior(
    candidate_id: UUID,
    pattern_type: str,
    signal_selected_candidate_id: UUID | None,
    signal_classification_status: str | None,
    signal_no_signal_reason: str | None,
    signal_risk_note_codes: set[str],
) -> str:
    if (
        signal_selected_candidate_id == candidate_id
        and is_blocker_pattern(pattern_type)
        and signal_classification_status == SignalClassificationStatus.NO_SIGNAL.value
        and (
            signal_no_signal_reason in BLOCKER_REASON_CODES
            or bool(signal_risk_note_codes & BLOCKER_REASON_CODES)
        )
    ):
        return "blocked"
    if signal_selected_candidate_id == candidate_id:
        return "selected"
    if signal_selected_candidate_id is not None:
        return "rejected"
    return "observed"


def is_blocker_pattern(pattern_type: str) -> bool:
    return pattern_type in BLOCKER_PATTERN_TYPES


def no_follow_through_count(observations: list[CandidateAttributionObservation]) -> int:
    count = 0
    for observation in observations:
        if (
            observation.outcome_label == OutcomeLabel.NO_FOLLOW_THROUGH.value
            or observation.behavior == "blocked"
            and observation.outcome_label
            in {
                OutcomeLabel.SIDEWAYS_AFTER_SIGNAL.value,
                OutcomeLabel.NOT_DIRECTIONAL.value,
            }
        ):
            count += 1
    return count


def count_behavior(observations: list[CandidateAttributionObservation], behavior: str) -> int:
    return sum(1 for observation in observations if observation.behavior == behavior)


def count_outcome(observations: list[CandidateAttributionObservation], label: str) -> int:
    return sum(1 for observation in observations if observation.outcome_label == label)


def rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return quantize_rate(Decimal(count) / Decimal(total))


def optional_rate(count: int, total: int) -> Decimal | None:
    if total == 0:
        return None
    return rate(count, total)


def max_rate(left: Decimal | None, right: Decimal | None) -> Decimal:
    return max(left or Decimal("0"), right or Decimal("0"))


def average_decimal(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return quantize_rate(sum(values, Decimal("0")) / Decimal(len(values)))


def average_optional_decimal(values: list[Decimal | None]) -> Decimal | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return average_decimal(present)


def quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


def decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(quantize_rate(value))


def counts_as_outcome_observation(
    behavior: str,
    outcome_label: str | None,
    evaluation_status: str | None,
) -> bool:
    if outcome_label is None:
        return False
    if behavior not in {"selected", "blocked"}:
        return False
    if outcome_label in {
        OutcomeLabel.CONTINUATION.value,
        OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value,
        OutcomeLabel.NO_FOLLOW_THROUGH.value,
        OutcomeLabel.REVERSAL.value,
        OutcomeLabel.INSUFFICIENT_DATA.value,
    }:
        return True
    return (
        behavior == "blocked"
        and evaluation_status == OutcomeEvaluationStatus.SKIPPED_NOT_DIRECTIONAL.value
        and outcome_label
        in {
            OutcomeLabel.SIDEWAYS_AFTER_SIGNAL.value,
            OutcomeLabel.NOT_DIRECTIONAL.value,
        }
    )


def outcome_values_for_observation(
    behavior: str,
    outcome_label: str | None,
    evaluation_status: str | None,
) -> tuple[str | None, str | None]:
    if counts_as_outcome_observation(behavior, outcome_label, evaluation_status):
        return outcome_label, evaluation_status
    return None, None


def sort_key(key: tuple[object, ...]) -> tuple[str, ...]:
    return tuple("" if value is None else str(value) for value in key)
