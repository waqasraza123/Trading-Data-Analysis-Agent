from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.profile_diagnostics.models import DiagnosticLabel
from app.modules.signals.models import SignalBias, SignalClassificationStatus

UNKNOWN_PATTERN = "unknown_pattern"
UNKNOWN_STRATEGY_PROFILE = "unknown_strategy_profile"


@dataclass(frozen=True)
class DiagnosticThresholds:
    strong_follow_through_rate: Decimal = Decimal("0.65")
    high_reversal_rate: Decimal = Decimal("0.35")
    high_no_follow_through_rate: Decimal = Decimal("0.40")
    confidence_misalignment_threshold: Decimal = Decimal("0.45")


@dataclass(frozen=True)
class DiagnosticOutcome:
    signal_id: UUID
    strategy_profile_key: str | None
    strategy_profile_version: str | None
    pattern_type: str | None
    symbol_id: UUID
    timeframe: str
    horizon_minutes: int
    bias: str
    classification_status: str
    evaluation_status: str
    outcome_label: str
    confidence_score: Decimal | None
    candidate_strength: Decimal | None
    max_favorable_move: Decimal
    max_adverse_move: Decimal
    net_move: Decimal
    max_favorable_pips: Decimal | None
    max_adverse_pips: Decimal | None
    net_pips: Decimal | None
    max_favorable_ticks: Decimal | None
    max_adverse_ticks: Decimal | None
    net_ticks: Decimal | None


@dataclass(frozen=True, kw_only=True)
class BaseDiagnosticResult:
    workspace_id: UUID
    horizon_minutes: int
    sample_size: int
    evaluated_count: int
    continuation_count: int
    partial_follow_through_count: int
    no_follow_through_count: int
    reversal_count: int
    insufficient_data_count: int
    continuation_rate: Decimal
    reversal_rate: Decimal
    no_follow_through_rate: Decimal
    average_confidence_score: Decimal | None
    average_max_favorable_move: Decimal | None
    average_max_adverse_move: Decimal | None
    average_net_move: Decimal | None
    average_max_favorable_pips: Decimal | None
    average_max_adverse_pips: Decimal | None
    average_net_pips: Decimal | None
    average_max_favorable_ticks: Decimal | None
    average_max_adverse_ticks: Decimal | None
    average_net_ticks: Decimal | None
    confidence_alignment_score: Decimal | None
    diagnostic_label: DiagnosticLabel
    diagnostic_summary: str
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class StrategyProfileDiagnosticResult(BaseDiagnosticResult):
    strategy_profile_key: str
    strategy_profile_version: str | None
    symbol_id: UUID | None
    timeframe: str | None


@dataclass(frozen=True, kw_only=True)
class PatternOutcomeDiagnosticResult(BaseDiagnosticResult):
    pattern_type: str
    strategy_profile_key: str | None
    symbol_id: UUID | None
    timeframe: str | None


class ProfileDiagnosticCalculator:
    def build_strategy_profile_diagnostics(
        self,
        workspace_id: UUID,
        outcomes: list[DiagnosticOutcome],
        minimum_sample_size: int,
        thresholds: DiagnosticThresholds,
    ) -> list[StrategyProfileDiagnosticResult]:
        grouped: dict[
            tuple[str, str | None, UUID | None, str | None, int], list[DiagnosticOutcome]
        ] = {}
        for outcome in outcomes:
            profile_key = outcome.strategy_profile_key or UNKNOWN_STRATEGY_PROFILE
            grouped.setdefault(
                (
                    profile_key,
                    outcome.strategy_profile_version,
                    None,
                    None,
                    outcome.horizon_minutes,
                ),
                [],
            ).append(outcome)
            grouped.setdefault(
                (
                    profile_key,
                    outcome.strategy_profile_version,
                    outcome.symbol_id,
                    outcome.timeframe,
                    outcome.horizon_minutes,
                ),
                [],
            ).append(outcome)
        return [
            self.calculate_strategy_profile_diagnostic(
                workspace_id=workspace_id,
                strategy_profile_key=key[0],
                strategy_profile_version=key[1],
                symbol_id=key[2],
                timeframe=key[3],
                horizon_minutes=key[4],
                outcomes=rows,
                minimum_sample_size=minimum_sample_size,
                thresholds=thresholds,
            )
            for key, rows in sorted(grouped.items(), key=lambda item: sort_key(item[0]))
        ]

    def build_pattern_diagnostics(
        self,
        workspace_id: UUID,
        outcomes: list[DiagnosticOutcome],
        minimum_sample_size: int,
        thresholds: DiagnosticThresholds,
    ) -> list[PatternOutcomeDiagnosticResult]:
        grouped: dict[
            tuple[str, str | None, UUID | None, str | None, int], list[DiagnosticOutcome]
        ] = {}
        for outcome in outcomes:
            pattern_type = outcome.pattern_type or UNKNOWN_PATTERN
            grouped.setdefault(
                (pattern_type, None, None, None, outcome.horizon_minutes), []
            ).append(outcome)
            grouped.setdefault(
                (
                    pattern_type,
                    outcome.strategy_profile_key,
                    outcome.symbol_id,
                    outcome.timeframe,
                    outcome.horizon_minutes,
                ),
                [],
            ).append(outcome)
        return [
            self.calculate_pattern_diagnostic(
                workspace_id=workspace_id,
                pattern_type=key[0],
                strategy_profile_key=key[1],
                symbol_id=key[2],
                timeframe=key[3],
                horizon_minutes=key[4],
                outcomes=rows,
                minimum_sample_size=minimum_sample_size,
                thresholds=thresholds,
            )
            for key, rows in sorted(grouped.items(), key=lambda item: sort_key(item[0]))
        ]

    def calculate_strategy_profile_diagnostic(
        self,
        workspace_id: UUID,
        strategy_profile_key: str,
        strategy_profile_version: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        horizon_minutes: int,
        outcomes: list[DiagnosticOutcome],
        minimum_sample_size: int,
        thresholds: DiagnosticThresholds,
    ) -> StrategyProfileDiagnosticResult:
        base = self.calculate_base_diagnostic(
            workspace_id=workspace_id,
            horizon_minutes=horizon_minutes,
            outcomes=outcomes,
            minimum_sample_size=minimum_sample_size,
            thresholds=thresholds,
            summary_subject=f"profile {strategy_profile_key}",
        )
        return StrategyProfileDiagnosticResult(
            **base.__dict__,
            strategy_profile_key=strategy_profile_key,
            strategy_profile_version=strategy_profile_version,
            symbol_id=symbol_id,
            timeframe=timeframe,
        )

    def calculate_pattern_diagnostic(
        self,
        workspace_id: UUID,
        pattern_type: str,
        strategy_profile_key: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        horizon_minutes: int,
        outcomes: list[DiagnosticOutcome],
        minimum_sample_size: int,
        thresholds: DiagnosticThresholds,
    ) -> PatternOutcomeDiagnosticResult:
        base = self.calculate_base_diagnostic(
            workspace_id=workspace_id,
            horizon_minutes=horizon_minutes,
            outcomes=outcomes,
            minimum_sample_size=minimum_sample_size,
            thresholds=thresholds,
            summary_subject=f"pattern {pattern_type}",
        )
        return PatternOutcomeDiagnosticResult(
            **base.__dict__,
            pattern_type=pattern_type,
            strategy_profile_key=strategy_profile_key,
            symbol_id=symbol_id,
            timeframe=timeframe,
        )

    def calculate_base_diagnostic(
        self,
        workspace_id: UUID,
        horizon_minutes: int,
        outcomes: list[DiagnosticOutcome],
        minimum_sample_size: int,
        thresholds: DiagnosticThresholds,
        summary_subject: str,
    ) -> BaseDiagnosticResult:
        evaluated = evaluated_directional_outcomes(outcomes)
        continuation_count = count_label(evaluated, OutcomeLabel.CONTINUATION.value)
        partial_count = count_label(evaluated, OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value)
        no_follow_count = count_label(evaluated, OutcomeLabel.NO_FOLLOW_THROUGH.value)
        reversal_count = count_label(evaluated, OutcomeLabel.REVERSAL.value)
        insufficient_count = count_label(outcomes, OutcomeLabel.INSUFFICIENT_DATA.value)
        evaluated_count = len(evaluated)
        continuation_rate = rate(continuation_count + partial_count, evaluated_count)
        reversal_rate = rate(reversal_count, evaluated_count)
        no_follow_rate = rate(no_follow_count, evaluated_count)
        alignment = confidence_alignment_score(evaluated, minimum_sample_size)
        high_confidence_weak_rate = weak_high_confidence_rate(evaluated)
        label = diagnostic_label(
            sample_size=evaluated_count,
            total_count=len(outcomes),
            insufficient_data_count=insufficient_count,
            continuation_rate=continuation_rate,
            reversal_rate=reversal_rate,
            no_follow_through_rate=no_follow_rate,
            confidence_alignment_score=alignment,
            high_confidence_weak_rate=high_confidence_weak_rate,
            minimum_sample_size=minimum_sample_size,
            thresholds=thresholds,
        )
        metadata_json: dict[str, object] = {
            "totalOutcomeCount": len(outcomes),
            "directionalEvaluatedOutcomeCount": evaluated_count,
            "highConfidenceWeakOutcomeRate": decimal_to_string(high_confidence_weak_rate),
            "minimumSampleSize": minimum_sample_size,
            "thresholds": {
                "strongFollowThroughRate": str(thresholds.strong_follow_through_rate),
                "highReversalRate": str(thresholds.high_reversal_rate),
                "highNoFollowThroughRate": str(thresholds.high_no_follow_through_rate),
                "confidenceMisalignmentThreshold": str(
                    thresholds.confidence_misalignment_threshold
                ),
            },
        }
        return BaseDiagnosticResult(
            workspace_id=workspace_id,
            horizon_minutes=horizon_minutes,
            sample_size=evaluated_count,
            evaluated_count=evaluated_count,
            continuation_count=continuation_count,
            partial_follow_through_count=partial_count,
            no_follow_through_count=no_follow_count,
            reversal_count=reversal_count,
            insufficient_data_count=insufficient_count,
            continuation_rate=quantize_rate(continuation_rate),
            reversal_rate=quantize_rate(reversal_rate),
            no_follow_through_rate=quantize_rate(no_follow_rate),
            average_confidence_score=average_optional_decimal(
                [outcome.confidence_score for outcome in evaluated]
            ),
            average_max_favorable_move=average_decimal(
                [outcome.max_favorable_move for outcome in evaluated]
            ),
            average_max_adverse_move=average_decimal(
                [outcome.max_adverse_move for outcome in evaluated]
            ),
            average_net_move=average_decimal([outcome.net_move for outcome in evaluated]),
            average_max_favorable_pips=average_optional_decimal(
                [outcome.max_favorable_pips for outcome in evaluated]
            ),
            average_max_adverse_pips=average_optional_decimal(
                [outcome.max_adverse_pips for outcome in evaluated]
            ),
            average_net_pips=average_optional_decimal([outcome.net_pips for outcome in evaluated]),
            average_max_favorable_ticks=average_optional_decimal(
                [outcome.max_favorable_ticks for outcome in evaluated]
            ),
            average_max_adverse_ticks=average_optional_decimal(
                [outcome.max_adverse_ticks for outcome in evaluated]
            ),
            average_net_ticks=average_optional_decimal(
                [outcome.net_ticks for outcome in evaluated]
            ),
            confidence_alignment_score=alignment,
            diagnostic_label=label,
            diagnostic_summary=diagnostic_summary(summary_subject, horizon_minutes, label),
            metadata_json=metadata_json,
        )


def evaluated_directional_outcomes(outcomes: list[DiagnosticOutcome]) -> list[DiagnosticOutcome]:
    return [
        outcome
        for outcome in outcomes
        if outcome.evaluation_status == OutcomeEvaluationStatus.EVALUATED.value
        and outcome.classification_status == SignalClassificationStatus.SIGNAL.value
        and outcome.bias in {SignalBias.BULLISH.value, SignalBias.BEARISH.value}
        and outcome.outcome_label
        in {
            OutcomeLabel.CONTINUATION.value,
            OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value,
            OutcomeLabel.NO_FOLLOW_THROUGH.value,
            OutcomeLabel.REVERSAL.value,
        }
    ]


def confidence_alignment_score(
    outcomes: list[DiagnosticOutcome],
    minimum_sample_size: int,
) -> Decimal | None:
    scored = [outcome for outcome in outcomes if outcome.confidence_score is not None]
    if len(scored) < minimum_sample_size:
        return None
    total = Decimal("0")
    for outcome in scored:
        confidence = outcome.confidence_score or Decimal("0")
        if outcome.outcome_label in {
            OutcomeLabel.CONTINUATION.value,
            OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value,
        }:
            total += confidence
        else:
            total += Decimal("1") - confidence
    return quantize_rate(total / Decimal(len(scored)))


def weak_high_confidence_rate(outcomes: list[DiagnosticOutcome]) -> Decimal:
    high_confidence = [
        outcome
        for outcome in outcomes
        if outcome.confidence_score is not None and outcome.confidence_score >= Decimal("0.7500")
    ]
    if not high_confidence:
        return Decimal("0")
    weak = [
        outcome
        for outcome in high_confidence
        if outcome.outcome_label
        in {OutcomeLabel.NO_FOLLOW_THROUGH.value, OutcomeLabel.REVERSAL.value}
    ]
    return Decimal(len(weak)) / Decimal(len(high_confidence))


def diagnostic_label(
    sample_size: int,
    total_count: int,
    insufficient_data_count: int,
    continuation_rate: Decimal,
    reversal_rate: Decimal,
    no_follow_through_rate: Decimal,
    confidence_alignment_score: Decimal | None,
    high_confidence_weak_rate: Decimal,
    minimum_sample_size: int,
    thresholds: DiagnosticThresholds,
) -> DiagnosticLabel:
    if sample_size == 0 and insufficient_data_count > 0:
        return DiagnosticLabel.INSUFFICIENT_DATA
    if sample_size < minimum_sample_size:
        return DiagnosticLabel.LOW_SAMPLE
    if total_count > 0 and Decimal(insufficient_data_count) / Decimal(total_count) >= Decimal(
        "0.50"
    ):
        return DiagnosticLabel.INSUFFICIENT_DATA
    if (
        confidence_alignment_score is not None
        and confidence_alignment_score <= thresholds.confidence_misalignment_threshold
    ) or high_confidence_weak_rate >= thresholds.confidence_misalignment_threshold:
        return DiagnosticLabel.NEEDS_THRESHOLD_REVIEW
    if reversal_rate >= thresholds.high_reversal_rate:
        return DiagnosticLabel.REVERSAL_PRONE
    if no_follow_through_rate >= thresholds.high_no_follow_through_rate:
        return DiagnosticLabel.NEEDS_THRESHOLD_REVIEW
    if (
        continuation_rate >= thresholds.strong_follow_through_rate
        and reversal_rate < thresholds.high_reversal_rate
        and no_follow_through_rate < thresholds.high_no_follow_through_rate
    ):
        return DiagnosticLabel.STRONG_FOLLOW_THROUGH
    if continuation_rate > Decimal("0") and (
        reversal_rate > Decimal("0") or no_follow_through_rate > Decimal("0")
    ):
        return DiagnosticLabel.MIXED_BEHAVIOR
    return DiagnosticLabel.NEUTRAL


def diagnostic_summary(subject: str, horizon_minutes: int, label: DiagnosticLabel) -> str:
    summaries = {
        DiagnosticLabel.STRONG_FOLLOW_THROUGH: (
            f"{subject} shows stronger historical follow-through at {horizon_minutes} minutes."
        ),
        DiagnosticLabel.MIXED_BEHAVIOR: (
            f"{subject} shows mixed observed behavior at {horizon_minutes} minutes."
        ),
        DiagnosticLabel.REVERSAL_PRONE: (
            f"{subject} shows elevated reversal behavior at {horizon_minutes} minutes."
        ),
        DiagnosticLabel.LOW_SAMPLE: (
            f"{subject} has too few evaluated outcomes for a stable diagnostic at "
            f"{horizon_minutes} minutes."
        ),
        DiagnosticLabel.INSUFFICIENT_DATA: (
            f"{subject} has insufficient evaluated outcome coverage at {horizon_minutes} minutes."
        ),
        DiagnosticLabel.NEEDS_THRESHOLD_REVIEW: (
            f"{subject} shows confidence or threshold calibration behavior to review at "
            f"{horizon_minutes} minutes."
        ),
        DiagnosticLabel.NEUTRAL: (
            f"{subject} has neutral observed behavior at {horizon_minutes} minutes."
        ),
    }
    return summaries[label]


def count_label(outcomes: list[DiagnosticOutcome], label: str) -> int:
    return sum(1 for outcome in outcomes if outcome.outcome_label == label)


def rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)


def average_decimal(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def average_optional_decimal(values: list[Decimal | None]) -> Decimal | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present, Decimal("0")) / Decimal(len(present))


def quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


def decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(quantize_rate(value))


def sort_key(key: tuple[object, ...]) -> tuple[str, ...]:
    return tuple("" if value is None else str(value) for value in key)


def apply_grouping(
    outcomes: list[DiagnosticOutcome],
    key_builder: Callable[[DiagnosticOutcome], tuple[object, ...]],
) -> dict[tuple[object, ...], list[DiagnosticOutcome]]:
    grouped: dict[tuple[object, ...], list[DiagnosticOutcome]] = {}
    for outcome in outcomes:
        grouped.setdefault(key_builder(outcome), []).append(outcome)
    return grouped
