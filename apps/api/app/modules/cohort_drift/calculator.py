from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.modules.cohort_drift.models import CohortDriftLabel, CohortDriftSeverity
from app.modules.cohort_drift.repository import CohortDriftOutcomeRow
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.signals.models import SignalBias, SignalClassificationStatus

UNKNOWN_VALUE = "unknown"
RATE_QUANT = Decimal("0.000001")


@dataclass(frozen=True)
class CohortDriftThresholds:
    mild_threshold: Decimal
    moderate_threshold: Decimal
    severe_threshold: Decimal


@dataclass(frozen=True)
class CohortWindowMetrics:
    sample_size: int
    evaluated_count: int
    continuation_rate: Decimal | None
    reversal_rate: Decimal | None
    no_follow_through_rate: Decimal | None
    confidence_alignment: Decimal | None
    continuation_count: int
    partial_follow_through_count: int
    reversal_count: int
    no_follow_through_count: int
    insufficient_data_count: int
    average_confidence_score: Decimal | None


@dataclass(frozen=True, kw_only=True)
class CohortDriftCalculationResult:
    workspace_id: UUID
    cohort_key: str
    cohort_dimensions_json: dict[str, object]
    horizon_minutes: int
    baseline_sample_size: int
    comparison_sample_size: int
    baseline_continuation_rate: Decimal | None
    comparison_continuation_rate: Decimal | None
    continuation_rate_delta: Decimal | None
    baseline_reversal_rate: Decimal | None
    comparison_reversal_rate: Decimal | None
    reversal_rate_delta: Decimal | None
    baseline_no_follow_through_rate: Decimal | None
    comparison_no_follow_through_rate: Decimal | None
    no_follow_through_delta: Decimal | None
    baseline_confidence_alignment: Decimal | None
    comparison_confidence_alignment: Decimal | None
    confidence_alignment_delta: Decimal | None
    drift_score: Decimal
    drift_label: CohortDriftLabel
    severity: CohortDriftSeverity
    summary: str
    metadata_json: dict[str, object] = field(default_factory=dict)


class CohortDriftCalculator:
    def calculate_results(
        self,
        workspace_id: UUID,
        baseline_rows: list[CohortDriftOutcomeRow],
        comparison_rows: list[CohortDriftOutcomeRow],
        dimensions: list[str],
        horizons_minutes: list[int],
        minimum_sample_size: int,
        thresholds: CohortDriftThresholds,
    ) -> list[CohortDriftCalculationResult]:
        baseline_groups = group_rows(baseline_rows, dimensions)
        comparison_groups = group_rows(comparison_rows, dimensions)
        result_keys = sorted(set(baseline_groups) | set(comparison_groups))
        results: list[CohortDriftCalculationResult] = []
        for key in result_keys:
            cohort_key_value, horizon = key
            if horizon not in horizons_minutes:
                continue
            baseline_metrics = calculate_metrics(
                baseline_groups.get(key, []),
                minimum_sample_size=minimum_sample_size,
            )
            comparison_metrics = calculate_metrics(
                comparison_groups.get(key, []),
                minimum_sample_size=minimum_sample_size,
            )
            dimensions_json = cohort_dimensions_from_key(cohort_key_value)
            results.append(
                compare_metrics(
                    workspace_id=workspace_id,
                    cohort_key_value=cohort_key_value,
                    cohort_dimensions_json=dimensions_json,
                    horizon_minutes=horizon,
                    baseline_metrics=baseline_metrics,
                    comparison_metrics=comparison_metrics,
                    minimum_sample_size=minimum_sample_size,
                    thresholds=thresholds,
                )
            )
        return results


def group_rows(
    rows: list[CohortDriftOutcomeRow],
    dimensions: list[str],
) -> dict[tuple[str, int], list[CohortDriftOutcomeRow]]:
    grouped: dict[tuple[str, int], list[CohortDriftOutcomeRow]] = {}
    for row in rows:
        key = cohort_key(row, dimensions)
        grouped.setdefault((key, row.horizon_minutes), []).append(row)
    return grouped


def cohort_key(row: CohortDriftOutcomeRow, dimensions: list[str]) -> str:
    values = cohort_dimension_values(row, dimensions)
    return "|".join(f"{key}={values[key]}" for key in sorted(values))


def cohort_dimension_values(
    row: CohortDriftOutcomeRow,
    dimensions: list[str],
) -> dict[str, str]:
    return {dimension: str(cohort_dimension_value(row, dimension)) for dimension in dimensions}


def cohort_dimension_value(row: CohortDriftOutcomeRow, dimension: str) -> object:
    if dimension == "strategy_profile_key":
        return row.strategy_profile_key or UNKNOWN_VALUE
    if dimension == "pattern_type":
        return row.pattern_type or UNKNOWN_VALUE
    if dimension == "symbol_id":
        return row.symbol_id
    if dimension == "timeframe":
        return row.timeframe
    if dimension == "bias":
        return row.bias
    if dimension == "confidence_label":
        return row.confidence_label
    if dimension == "market_session_label":
        return row.market_session_label or UNKNOWN_VALUE
    if dimension == "market_regime_label":
        return row.market_regime_label or UNKNOWN_VALUE
    return UNKNOWN_VALUE


def cohort_dimensions_from_key(cohort_key_value: str) -> dict[str, object]:
    dimensions: dict[str, object] = {}
    for segment in cohort_key_value.split("|"):
        key, _, value = segment.partition("=")
        if key:
            dimensions[key] = value
    return dimensions


def calculate_metrics(
    rows: list[CohortDriftOutcomeRow],
    minimum_sample_size: int,
) -> CohortWindowMetrics:
    directional = directional_rows(rows)
    evaluated = evaluated_rows(directional)
    continuation_count = count_label(evaluated, OutcomeLabel.CONTINUATION.value)
    partial_count = count_label(evaluated, OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value)
    reversal_count = count_label(evaluated, OutcomeLabel.REVERSAL.value)
    no_follow_count = count_label(evaluated, OutcomeLabel.NO_FOLLOW_THROUGH.value)
    insufficient_count = count_insufficient(directional)
    evaluated_count = len(evaluated)
    continuation_rate = optional_rate(continuation_count + partial_count, evaluated_count)
    reversal_rate = optional_rate(reversal_count, evaluated_count)
    no_follow_rate = optional_rate(no_follow_count, evaluated_count)
    average_confidence = average_decimal([row.confidence_score for row in evaluated])
    alignment = confidence_alignment(
        average_confidence=average_confidence,
        continuation_rate=continuation_rate,
        evaluated_count=evaluated_count,
        minimum_sample_size=minimum_sample_size,
    )
    return CohortWindowMetrics(
        sample_size=len(directional),
        evaluated_count=evaluated_count,
        continuation_rate=continuation_rate,
        reversal_rate=reversal_rate,
        no_follow_through_rate=no_follow_rate,
        confidence_alignment=alignment,
        continuation_count=continuation_count,
        partial_follow_through_count=partial_count,
        reversal_count=reversal_count,
        no_follow_through_count=no_follow_count,
        insufficient_data_count=insufficient_count,
        average_confidence_score=quantize_rate(average_confidence)
        if average_confidence is not None
        else None,
    )


def compare_metrics(
    workspace_id: UUID,
    cohort_key_value: str,
    cohort_dimensions_json: dict[str, object],
    horizon_minutes: int,
    baseline_metrics: CohortWindowMetrics,
    comparison_metrics: CohortWindowMetrics,
    minimum_sample_size: int,
    thresholds: CohortDriftThresholds,
) -> CohortDriftCalculationResult:
    continuation_delta = nullable_delta(
        comparison_metrics.continuation_rate,
        baseline_metrics.continuation_rate,
    )
    reversal_delta = nullable_delta(
        comparison_metrics.reversal_rate,
        baseline_metrics.reversal_rate,
    )
    no_follow_delta = nullable_delta(
        comparison_metrics.no_follow_through_rate,
        baseline_metrics.no_follow_through_rate,
    )
    alignment_delta = nullable_delta(
        comparison_metrics.confidence_alignment,
        baseline_metrics.confidence_alignment,
    )
    score = drift_score(
        continuation_delta=continuation_delta,
        reversal_delta=reversal_delta,
        no_follow_delta=no_follow_delta,
        alignment_delta=alignment_delta,
    )
    label = drift_label(
        baseline_metrics=baseline_metrics,
        comparison_metrics=comparison_metrics,
        minimum_sample_size=minimum_sample_size,
        drift_score_value=score,
        thresholds=thresholds,
    )
    severity = drift_severity(label)
    return CohortDriftCalculationResult(
        workspace_id=workspace_id,
        cohort_key=cohort_key_value,
        cohort_dimensions_json=cohort_dimensions_json,
        horizon_minutes=horizon_minutes,
        baseline_sample_size=baseline_metrics.sample_size,
        comparison_sample_size=comparison_metrics.sample_size,
        baseline_continuation_rate=baseline_metrics.continuation_rate,
        comparison_continuation_rate=comparison_metrics.continuation_rate,
        continuation_rate_delta=continuation_delta,
        baseline_reversal_rate=baseline_metrics.reversal_rate,
        comparison_reversal_rate=comparison_metrics.reversal_rate,
        reversal_rate_delta=reversal_delta,
        baseline_no_follow_through_rate=baseline_metrics.no_follow_through_rate,
        comparison_no_follow_through_rate=comparison_metrics.no_follow_through_rate,
        no_follow_through_delta=no_follow_delta,
        baseline_confidence_alignment=baseline_metrics.confidence_alignment,
        comparison_confidence_alignment=comparison_metrics.confidence_alignment,
        confidence_alignment_delta=alignment_delta,
        drift_score=score,
        drift_label=label,
        severity=severity,
        summary=result_summary(
            label,
            severity,
            horizon_minutes,
            baseline_metrics,
            comparison_metrics,
            score,
        ),
        metadata_json={
            "minimumSampleSize": minimum_sample_size,
            "baselineEvaluatedCount": baseline_metrics.evaluated_count,
            "comparisonEvaluatedCount": comparison_metrics.evaluated_count,
            "baselineAverageConfidenceScore": decimal_to_string(
                baseline_metrics.average_confidence_score
            ),
            "comparisonAverageConfidenceScore": decimal_to_string(
                comparison_metrics.average_confidence_score
            ),
            "baselineCounts": metric_counts(baseline_metrics),
            "comparisonCounts": metric_counts(comparison_metrics),
            "thresholds": {
                "mild": str(thresholds.mild_threshold),
                "moderate": str(thresholds.moderate_threshold),
                "severe": str(thresholds.severe_threshold),
            },
            "reviewRecommended": label
            in {
                CohortDriftLabel.MILD_DRIFT,
                CohortDriftLabel.MODERATE_DRIFT,
                CohortDriftLabel.SEVERE_DRIFT,
            },
        },
    )


def directional_rows(rows: list[CohortDriftOutcomeRow]) -> list[CohortDriftOutcomeRow]:
    return [
        row
        for row in rows
        if row.classification_status == SignalClassificationStatus.SIGNAL.value
        and row.bias in {SignalBias.BULLISH.value, SignalBias.BEARISH.value}
    ]


def evaluated_rows(rows: list[CohortDriftOutcomeRow]) -> list[CohortDriftOutcomeRow]:
    return [
        row
        for row in rows
        if row.evaluation_status == OutcomeEvaluationStatus.EVALUATED.value
        and row.outcome_label
        in {
            OutcomeLabel.CONTINUATION.value,
            OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value,
            OutcomeLabel.NO_FOLLOW_THROUGH.value,
            OutcomeLabel.REVERSAL.value,
        }
    ]


def count_label(rows: list[CohortDriftOutcomeRow], label: str) -> int:
    return sum(1 for row in rows if row.outcome_label == label)


def count_insufficient(rows: list[CohortDriftOutcomeRow]) -> int:
    return sum(
        1
        for row in rows
        if row.outcome_label == OutcomeLabel.INSUFFICIENT_DATA.value
        or row.evaluation_status == OutcomeEvaluationStatus.INSUFFICIENT_FUTURE_DATA.value
    )


def optional_rate(count: int, total: int) -> Decimal | None:
    if total == 0:
        return None
    return quantize_rate(Decimal(count) / Decimal(total))


def average_decimal(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def confidence_alignment(
    average_confidence: Decimal | None,
    continuation_rate: Decimal | None,
    evaluated_count: int,
    minimum_sample_size: int,
) -> Decimal | None:
    if (
        average_confidence is None
        or continuation_rate is None
        or evaluated_count < minimum_sample_size
    ):
        return None
    score = Decimal("1") - abs(average_confidence - continuation_rate)
    return quantize_rate(min(Decimal("1"), max(Decimal("0"), score)))


def nullable_delta(
    comparison_value: Decimal | None,
    baseline_value: Decimal | None,
) -> Decimal | None:
    if comparison_value is None or baseline_value is None:
        return None
    return quantize_rate(comparison_value - baseline_value)


def drift_score(
    continuation_delta: Decimal | None,
    reversal_delta: Decimal | None,
    no_follow_delta: Decimal | None,
    alignment_delta: Decimal | None,
) -> Decimal:
    values = [
        abs(value)
        for value in [
            continuation_delta,
            reversal_delta,
            no_follow_delta,
            alignment_delta,
        ]
        if value is not None
    ]
    if not values:
        return Decimal("0.000000")
    return quantize_rate(max(values))


def drift_label(
    baseline_metrics: CohortWindowMetrics,
    comparison_metrics: CohortWindowMetrics,
    minimum_sample_size: int,
    drift_score_value: Decimal,
    thresholds: CohortDriftThresholds,
) -> CohortDriftLabel:
    if baseline_metrics.evaluated_count == 0 or comparison_metrics.evaluated_count == 0:
        return CohortDriftLabel.INSUFFICIENT_DATA
    if (
        baseline_metrics.sample_size < minimum_sample_size
        or comparison_metrics.sample_size < minimum_sample_size
    ):
        return CohortDriftLabel.LOW_SAMPLE
    if drift_score_value >= thresholds.severe_threshold:
        return CohortDriftLabel.SEVERE_DRIFT
    if drift_score_value >= thresholds.moderate_threshold:
        return CohortDriftLabel.MODERATE_DRIFT
    if drift_score_value >= thresholds.mild_threshold:
        return CohortDriftLabel.MILD_DRIFT
    return CohortDriftLabel.NO_DRIFT


def drift_severity(label: CohortDriftLabel) -> CohortDriftSeverity:
    if label == CohortDriftLabel.SEVERE_DRIFT:
        return CohortDriftSeverity.HIGH
    if label == CohortDriftLabel.MODERATE_DRIFT:
        return CohortDriftSeverity.MEDIUM
    if label == CohortDriftLabel.MILD_DRIFT:
        return CohortDriftSeverity.LOW
    return CohortDriftSeverity.INFO


def result_summary(
    label: CohortDriftLabel,
    severity: CohortDriftSeverity,
    horizon_minutes: int,
    baseline_metrics: CohortWindowMetrics,
    comparison_metrics: CohortWindowMetrics,
    score: Decimal,
) -> str:
    if label == CohortDriftLabel.INSUFFICIENT_DATA:
        return (
            f"Horizon {horizon_minutes} has insufficient evaluated stored outcomes for "
            "baseline versus recent-window drift detection."
        )
    if label == CohortDriftLabel.LOW_SAMPLE:
        return (
            f"Horizon {horizon_minutes} has low sample coverage: baseline "
            f"{baseline_metrics.sample_size}, recent window {comparison_metrics.sample_size}."
        )
    if label == CohortDriftLabel.NO_DRIFT:
        return f"Horizon {horizon_minutes} shows no material cohort drift. Drift score {score}."
    return (
        f"Horizon {horizon_minutes} shows {label.value} with {severity.value} severity. "
        f"Review recommended. Drift score {score}."
    )


def metric_counts(metrics: CohortWindowMetrics) -> dict[str, int]:
    return {
        "evaluated": metrics.evaluated_count,
        "continuation": metrics.continuation_count,
        "partialFollowThrough": metrics.partial_follow_through_count,
        "reversal": metrics.reversal_count,
        "noFollowThrough": metrics.no_follow_through_count,
        "insufficientData": metrics.insufficient_data_count,
    }


def quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)
