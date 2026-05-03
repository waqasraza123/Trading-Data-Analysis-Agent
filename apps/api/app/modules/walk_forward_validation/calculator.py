from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.signals.models import SignalBias, SignalClassificationStatus
from app.modules.walk_forward_validation.models import WalkForwardStabilityLabel
from app.modules.walk_forward_validation.repository import WalkForwardOutcomeRow


@dataclass(frozen=True)
class WalkForwardWindowRange:
    window_index: int
    window_start: datetime
    window_end: datetime


@dataclass(frozen=True, kw_only=True)
class WalkForwardWindowResult:
    workspace_id: UUID
    window_index: int
    window_start: datetime
    window_end: datetime
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
    confidence_alignment_score: Decimal | None
    stability_label: WalkForwardStabilityLabel
    summary: str
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class WalkForwardComparisonResult:
    workspace_id: UUID
    horizon_minutes: int
    compared_window_count: int
    stability_score: Decimal
    degradation_detected: bool
    improvement_detected: bool
    summary: str
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class WalkForwardThresholds:
    degradation_threshold: Decimal
    improvement_threshold: Decimal


class WalkForwardValidationCalculator:
    def split_windows(
        self,
        start_time: datetime,
        end_time: datetime,
        window_days: int,
    ) -> list[WalkForwardWindowRange]:
        if start_time > end_time:
            return []
        window_delta = timedelta(days=window_days)
        windows: list[WalkForwardWindowRange] = []
        current_start = start_time
        index = 0
        while current_start <= end_time:
            current_end = min(current_start + window_delta, end_time)
            windows.append(
                WalkForwardWindowRange(
                    window_index=index,
                    window_start=current_start,
                    window_end=current_end,
                )
            )
            if current_end >= end_time:
                break
            current_start = current_end
            index += 1
        return windows

    def calculate_windows(
        self,
        workspace_id: UUID,
        rows: list[WalkForwardOutcomeRow],
        windows: list[WalkForwardWindowRange],
        horizons_minutes: list[int],
        minimum_sample_size: int,
        thresholds: WalkForwardThresholds,
    ) -> list[WalkForwardWindowResult]:
        results: list[WalkForwardWindowResult] = []
        previous_by_horizon: dict[int, WalkForwardWindowResult] = {}
        for window in windows:
            for horizon in horizons_minutes:
                window_rows = [
                    row
                    for row in rows
                    if row.horizon_minutes == horizon and row_in_window(row, window, len(windows))
                ]
                previous = previous_by_horizon.get(horizon)
                result = calculate_window_result(
                    workspace_id=workspace_id,
                    window=window,
                    horizon_minutes=horizon,
                    rows=window_rows,
                    minimum_sample_size=minimum_sample_size,
                    thresholds=thresholds,
                    previous=previous,
                )
                results.append(result)
                if result.stability_label not in {
                    WalkForwardStabilityLabel.LOW_SAMPLE,
                    WalkForwardStabilityLabel.INSUFFICIENT_DATA,
                }:
                    previous_by_horizon[horizon] = result
        return results

    def compare_windows(
        self,
        workspace_id: UUID,
        window_results: list[WalkForwardWindowResult],
        horizons_minutes: list[int],
        thresholds: WalkForwardThresholds,
    ) -> list[WalkForwardComparisonResult]:
        return [
            compare_horizon_windows(
                workspace_id=workspace_id,
                horizon_minutes=horizon,
                results=[
                    result
                    for result in window_results
                    if result.horizon_minutes == horizon
                    and result.stability_label
                    not in {
                        WalkForwardStabilityLabel.LOW_SAMPLE,
                        WalkForwardStabilityLabel.INSUFFICIENT_DATA,
                    }
                ],
                thresholds=thresholds,
            )
            for horizon in horizons_minutes
        ]


def row_in_window(
    row: WalkForwardOutcomeRow,
    window: WalkForwardWindowRange,
    window_count: int,
) -> bool:
    if window.window_index == window_count - 1:
        return window.window_start <= row.reference_time <= window.window_end
    return window.window_start <= row.reference_time < window.window_end


def calculate_window_result(
    workspace_id: UUID,
    window: WalkForwardWindowRange,
    horizon_minutes: int,
    rows: list[WalkForwardOutcomeRow],
    minimum_sample_size: int,
    thresholds: WalkForwardThresholds,
    previous: WalkForwardWindowResult | None,
) -> WalkForwardWindowResult:
    directional = directional_rows(rows)
    evaluated = evaluated_rows(directional)
    continuation_count = count_label(evaluated, OutcomeLabel.CONTINUATION.value)
    partial_count = count_label(evaluated, OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value)
    no_follow_count = count_label(evaluated, OutcomeLabel.NO_FOLLOW_THROUGH.value)
    reversal_count = count_label(evaluated, OutcomeLabel.REVERSAL.value)
    insufficient_count = count_insufficient(directional)
    evaluated_count = len(evaluated)
    continuation_rate = quantize_rate(rate(continuation_count + partial_count, evaluated_count))
    reversal_rate = quantize_rate(rate(reversal_count, evaluated_count))
    no_follow_rate = quantize_rate(rate(no_follow_count, evaluated_count))
    average_confidence = average_decimal([row.confidence_score for row in evaluated])
    alignment = confidence_alignment_score(evaluated, average_confidence, minimum_sample_size)
    label = stability_label(
        sample_size=len(directional),
        evaluated_count=evaluated_count,
        minimum_sample_size=minimum_sample_size,
        current_continuation_rate=continuation_rate,
        current_reversal_rate=reversal_rate,
        current_alignment=alignment,
        previous=previous,
        thresholds=thresholds,
    )
    return WalkForwardWindowResult(
        workspace_id=workspace_id,
        window_index=window.window_index,
        window_start=window.window_start,
        window_end=window.window_end,
        horizon_minutes=horizon_minutes,
        sample_size=len(directional),
        evaluated_count=evaluated_count,
        continuation_count=continuation_count,
        partial_follow_through_count=partial_count,
        no_follow_through_count=no_follow_count,
        reversal_count=reversal_count,
        insufficient_data_count=insufficient_count,
        continuation_rate=continuation_rate,
        reversal_rate=reversal_rate,
        no_follow_through_rate=no_follow_rate,
        average_confidence_score=quantize_rate(average_confidence) if average_confidence is not None else None,
        confidence_alignment_score=alignment,
        stability_label=label,
        summary=window_summary(label, window.window_index, horizon_minutes, len(directional), evaluated_count),
        metadata_json={
            "minimumSampleSize": minimum_sample_size,
            "observedFollowThroughRate": str(continuation_rate),
            "alignmentDenominator": evaluated_count if alignment is not None else 0,
            "previousSufficientWindowIndex": previous.window_index if previous is not None else None,
            "continuationRateDelta": (
                str(quantize_rate(continuation_rate - previous.continuation_rate))
                if previous is not None
                else None
            ),
            "reversalRateDelta": (
                str(quantize_rate(reversal_rate - previous.reversal_rate))
                if previous is not None
                else None
            ),
        },
    )


def compare_horizon_windows(
    workspace_id: UUID,
    horizon_minutes: int,
    results: list[WalkForwardWindowResult],
    thresholds: WalkForwardThresholds,
) -> WalkForwardComparisonResult:
    ordered = sorted(results, key=lambda result: result.window_index)
    compared_count = len(ordered)
    if compared_count < 2:
        return WalkForwardComparisonResult(
            workspace_id=workspace_id,
            horizon_minutes=horizon_minutes,
            compared_window_count=compared_count,
            stability_score=Decimal("0.000000"),
            degradation_detected=False,
            improvement_detected=False,
            summary=(
                f"Horizon {horizon_minutes} has fewer than two sufficient validation windows "
                "for stability comparison."
            ),
            metadata_json={"sufficientWindowIndexes": [result.window_index for result in ordered]},
        )
    first = ordered[0]
    last = ordered[-1]
    continuation_delta = quantize_rate(last.continuation_rate - first.continuation_rate)
    reversal_delta = quantize_rate(last.reversal_rate - first.reversal_rate)
    alignment_delta = alignment_delta_value(first, last)
    degradation_detected = (
        -continuation_delta >= thresholds.degradation_threshold
        or reversal_delta >= thresholds.degradation_threshold
        or (alignment_delta is not None and -alignment_delta >= thresholds.degradation_threshold)
    )
    improvement_detected = (
        continuation_delta >= thresholds.improvement_threshold
        or -reversal_delta >= thresholds.improvement_threshold
        or (alignment_delta is not None and alignment_delta >= thresholds.improvement_threshold)
    )
    stability_score = horizon_stability_score(ordered)
    return WalkForwardComparisonResult(
        workspace_id=workspace_id,
        horizon_minutes=horizon_minutes,
        compared_window_count=compared_count,
        stability_score=stability_score,
        degradation_detected=degradation_detected,
        improvement_detected=improvement_detected,
        summary=comparison_summary(
            horizon_minutes=horizon_minutes,
            compared_count=compared_count,
            degradation_detected=degradation_detected,
            improvement_detected=improvement_detected,
        ),
        metadata_json={
            "firstWindowIndex": first.window_index,
            "lastWindowIndex": last.window_index,
            "continuationRateDelta": str(continuation_delta),
            "reversalRateDelta": str(reversal_delta),
            "confidenceAlignmentDelta": str(alignment_delta) if alignment_delta is not None else None,
            "degradationThreshold": str(thresholds.degradation_threshold),
            "improvementThreshold": str(thresholds.improvement_threshold),
        },
    )


def directional_rows(rows: list[WalkForwardOutcomeRow]) -> list[WalkForwardOutcomeRow]:
    return [
        row
        for row in rows
        if row.classification_status == SignalClassificationStatus.SIGNAL.value
        and row.bias in {SignalBias.BULLISH.value, SignalBias.BEARISH.value}
    ]


def evaluated_rows(rows: list[WalkForwardOutcomeRow]) -> list[WalkForwardOutcomeRow]:
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


def count_label(rows: list[WalkForwardOutcomeRow], label: str) -> int:
    return sum(1 for row in rows if row.outcome_label == label)


def count_insufficient(rows: list[WalkForwardOutcomeRow]) -> int:
    return sum(
        1
        for row in rows
        if row.outcome_label == OutcomeLabel.INSUFFICIENT_DATA.value
        or row.evaluation_status == OutcomeEvaluationStatus.INSUFFICIENT_FUTURE_DATA.value
    )


def rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)


def average_decimal(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def confidence_alignment_score(
    evaluated: list[WalkForwardOutcomeRow],
    average_confidence: Decimal | None,
    minimum_sample_size: int,
) -> Decimal | None:
    if average_confidence is None or len(evaluated) < minimum_sample_size:
        return None
    observed_follow_through_rate = rate(
        count_label(evaluated, OutcomeLabel.CONTINUATION.value)
        + count_label(evaluated, OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value),
        len(evaluated),
    )
    score = Decimal("1") - abs(average_confidence - observed_follow_through_rate)
    return quantize_rate(min(Decimal("1"), max(Decimal("0"), score)))


def stability_label(
    sample_size: int,
    evaluated_count: int,
    minimum_sample_size: int,
    current_continuation_rate: Decimal,
    current_reversal_rate: Decimal,
    current_alignment: Decimal | None,
    previous: WalkForwardWindowResult | None,
    thresholds: WalkForwardThresholds,
) -> WalkForwardStabilityLabel:
    if sample_size == 0 or evaluated_count == 0:
        return WalkForwardStabilityLabel.INSUFFICIENT_DATA
    if evaluated_count < minimum_sample_size:
        return WalkForwardStabilityLabel.LOW_SAMPLE
    if previous is None:
        return WalkForwardStabilityLabel.STABLE
    continuation_delta = current_continuation_rate - previous.continuation_rate
    reversal_delta = current_reversal_rate - previous.reversal_rate
    alignment_delta = (
        current_alignment - previous.confidence_alignment_score
        if current_alignment is not None and previous.confidence_alignment_score is not None
        else None
    )
    degrading = (
        -continuation_delta >= thresholds.degradation_threshold
        or reversal_delta >= thresholds.degradation_threshold
        or (alignment_delta is not None and -alignment_delta >= thresholds.degradation_threshold)
    )
    improving = (
        continuation_delta >= thresholds.improvement_threshold
        or -reversal_delta >= thresholds.improvement_threshold
        or (alignment_delta is not None and alignment_delta >= thresholds.improvement_threshold)
    )
    if degrading and improving:
        return WalkForwardStabilityLabel.MIXED
    if degrading:
        return WalkForwardStabilityLabel.DEGRADING
    if improving:
        return WalkForwardStabilityLabel.IMPROVING
    return WalkForwardStabilityLabel.STABLE


def horizon_stability_score(results: list[WalkForwardWindowResult]) -> Decimal:
    if len(results) < 2:
        return Decimal("0.000000")
    differences: list[Decimal] = []
    previous = results[0]
    for current in results[1:]:
        differences.append(abs(current.continuation_rate - previous.continuation_rate))
        differences.append(abs(current.reversal_rate - previous.reversal_rate))
        if (
            current.confidence_alignment_score is not None
            and previous.confidence_alignment_score is not None
        ):
            differences.append(abs(current.confidence_alignment_score - previous.confidence_alignment_score))
        previous = current
    average_difference = sum(differences, Decimal("0")) / Decimal(len(differences))
    return quantize_rate(max(Decimal("0"), Decimal("1") - average_difference))


def alignment_delta_value(
    first: WalkForwardWindowResult,
    last: WalkForwardWindowResult,
) -> Decimal | None:
    if first.confidence_alignment_score is None or last.confidence_alignment_score is None:
        return None
    return quantize_rate(last.confidence_alignment_score - first.confidence_alignment_score)


def window_summary(
    label: WalkForwardStabilityLabel,
    window_index: int,
    horizon_minutes: int,
    sample_size: int,
    evaluated_count: int,
) -> str:
    return (
        f"Validation window {window_index} at {horizon_minutes} minutes is {label.value} "
        f"with {sample_size} stored directional outcomes and {evaluated_count} evaluated outcomes."
    )


def comparison_summary(
    horizon_minutes: int,
    compared_count: int,
    degradation_detected: bool,
    improvement_detected: bool,
) -> str:
    if degradation_detected and improvement_detected:
        movement = "mixed stability changes"
    elif degradation_detected:
        movement = "degradation behavior"
    elif improvement_detected:
        movement = "improvement behavior"
    else:
        movement = "stable behavior"
    return (
        f"Horizon {horizon_minutes} compared {compared_count} sufficient validation windows "
        f"and found {movement}."
    )


def quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))
