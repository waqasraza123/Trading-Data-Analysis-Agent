from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from math import sqrt
from uuid import UUID

from app.modules.cross_asset_context.models import (
    CrossAssetAlignmentLabel,
    CrossAssetDataQualityLabel,
    CrossAssetLeadLagLabel,
)

DECIMAL_SCORE_QUANT = Decimal("0.00001")
DECIMAL_MOVE_QUANT = Decimal("0.0000000001")
MIN_LEAD_LAG_OVERLAP = 3
FLAT_MOVE_EPSILON = 0.0000001


@dataclass(frozen=True)
class CrossAssetCandleSnapshot:
    timestamp: datetime
    open: Decimal
    close: Decimal


@dataclass(frozen=True)
class CrossAssetCalculationInput:
    base_symbol_id: UUID
    compared_symbol_id: UUID
    timeframe: str
    start_time: datetime
    end_time: datetime
    base_candles: list[CrossAssetCandleSnapshot]
    compared_candles: list[CrossAssetCandleSnapshot]
    min_candles: int
    lead_lag_max_offset: int
    alignment_threshold: Decimal
    divergence_threshold: Decimal


@dataclass(frozen=True)
class CrossAssetCalculationResult:
    base_move: Decimal
    compared_move: Decimal
    base_direction: str
    compared_direction: str
    correlation_score: Decimal
    alignment_label: CrossAssetAlignmentLabel
    lead_lag_offset_candles: int | None
    lead_lag_label: CrossAssetLeadLagLabel
    divergence_score: Decimal
    data_quality_label: CrossAssetDataQualityLabel
    metadata_json: dict[str, object]


class CrossAssetContextCalculator:
    def calculate(self, payload: CrossAssetCalculationInput) -> CrossAssetCalculationResult:
        base_series = movement_series(payload.base_candles)
        compared_series = movement_series(payload.compared_candles)
        aligned = align_series(base_series, compared_series)
        overlap_count = len(aligned)
        data_quality_label = data_quality(
            overlap_count=overlap_count,
            base_count=len(base_series),
            compared_count=len(compared_series),
            min_candles=payload.min_candles,
        )
        base_total_move = total_move(payload.base_candles)
        compared_total_move = total_move(payload.compared_candles)
        if overlap_count < payload.min_candles:
            return CrossAssetCalculationResult(
                base_move=base_total_move,
                compared_move=compared_total_move,
                base_direction=direction_for_move(base_total_move),
                compared_direction=direction_for_move(compared_total_move),
                correlation_score=Decimal("0.00000"),
                alignment_label=CrossAssetAlignmentLabel.INSUFFICIENT_DATA,
                lead_lag_offset_candles=None,
                lead_lag_label=CrossAssetLeadLagLabel.INSUFFICIENT_DATA,
                divergence_score=Decimal("0.00000"),
                data_quality_label=CrossAssetDataQualityLabel.INSUFFICIENT_DATA,
                metadata_json=insufficient_metadata(payload, overlap_count, data_quality_label),
            )
        base_moves = [pair[0] for pair in aligned]
        compared_moves = [pair[1] for pair in aligned]
        correlation_score = quantize_score(pearson_correlation(base_moves, compared_moves))
        alignment_ratio = directional_alignment_ratio(base_moves, compared_moves)
        conflict_ratio = directional_conflict_ratio(base_moves, compared_moves)
        divergence_score = quantize_score(
            max(conflict_ratio, abs(float(correlation_score)) if correlation_score < 0 else 0.0)
        )
        alignment_label = label_alignment(
            correlation_score=correlation_score,
            alignment_ratio=alignment_ratio,
            conflict_ratio=conflict_ratio,
            divergence_score=divergence_score,
            alignment_threshold=payload.alignment_threshold,
            divergence_threshold=payload.divergence_threshold,
        )
        lead_lag = lead_lag_relationship(
            aligned=aligned,
            max_offset=payload.lead_lag_max_offset,
            min_candles=payload.min_candles,
            relationship_threshold=payload.alignment_threshold,
        )
        metadata_json = {
            "baseSymbolId": str(payload.base_symbol_id),
            "comparedSymbolId": str(payload.compared_symbol_id),
            "timeframe": payload.timeframe,
            "overlapCandleCount": overlap_count,
            "baseCandleCount": len(base_series),
            "comparedCandleCount": len(compared_series),
            "alignmentRatio": str(quantize_score(alignment_ratio)),
            "conflictRatio": str(quantize_score(conflict_ratio)),
            "leadLagCandidates": lead_lag.candidates,
            "method": "normalized_directional_movement_correlation_v1",
            "languagePolicy": {
                "contextOnly": True,
                "noCausation": True,
                "noFinancialAdvice": True,
            },
        }
        return CrossAssetCalculationResult(
            base_move=base_total_move,
            compared_move=compared_total_move,
            base_direction=direction_for_move(base_total_move),
            compared_direction=direction_for_move(compared_total_move),
            correlation_score=correlation_score,
            alignment_label=alignment_label,
            lead_lag_offset_candles=lead_lag.offset_candles,
            lead_lag_label=lead_lag.label,
            divergence_score=divergence_score,
            data_quality_label=data_quality_label,
            metadata_json=metadata_json,
        )


@dataclass(frozen=True)
class LeadLagCalculation:
    offset_candles: int | None
    label: CrossAssetLeadLagLabel
    candidates: list[dict[str, object]]


def movement_series(candles: list[CrossAssetCandleSnapshot]) -> list[tuple[datetime, float]]:
    values: list[tuple[datetime, float]] = []
    for candle in candles:
        if candle.open <= 0:
            continue
        values.append((candle.timestamp, float((candle.close - candle.open) / candle.open)))
    return values


def align_series(
    base_series: list[tuple[datetime, float]],
    compared_series: list[tuple[datetime, float]],
) -> list[tuple[float, float]]:
    compared_by_timestamp = {timestamp: value for timestamp, value in compared_series}
    return [
        (base_value, compared_by_timestamp[timestamp])
        for timestamp, base_value in base_series
        if timestamp in compared_by_timestamp
    ]


def total_move(candles: list[CrossAssetCandleSnapshot]) -> Decimal:
    if not candles:
        return Decimal("0.0000000000")
    first = candles[0]
    last = candles[-1]
    if first.open <= 0:
        return Decimal("0.0000000000")
    return ((last.close - first.open) / first.open).quantize(
        DECIMAL_MOVE_QUANT,
        rounding=ROUND_HALF_UP,
    )


def direction_for_move(value: Decimal) -> str:
    if value > Decimal("0"):
        return "up"
    if value < Decimal("0"):
        return "down"
    return "flat"


def pearson_correlation(left_values: list[float], right_values: list[float]) -> float:
    if len(left_values) != len(right_values) or len(left_values) < 2:
        return 0.0
    left_mean = sum(left_values) / len(left_values)
    right_mean = sum(right_values) / len(right_values)
    numerator = sum(
        (left - left_mean) * (right - right_mean)
        for left, right in zip(left_values, right_values, strict=False)
    )
    left_variance = sum((left - left_mean) ** 2 for left in left_values)
    right_variance = sum((right - right_mean) ** 2 for right in right_values)
    denominator = sqrt(left_variance * right_variance)
    if denominator == 0:
        return 0.0
    return max(min(numerator / denominator, 1.0), -1.0)


def directional_alignment_ratio(left_values: list[float], right_values: list[float]) -> float:
    directional_pairs = [
        (left, right)
        for left, right in zip(left_values, right_values, strict=False)
        if abs(left) > FLAT_MOVE_EPSILON or abs(right) > FLAT_MOVE_EPSILON
    ]
    if not directional_pairs:
        return 0.0
    aligned_count = sum(
        1 for left, right in directional_pairs if signed_direction(left) == signed_direction(right)
    )
    return aligned_count / len(directional_pairs)


def directional_conflict_ratio(left_values: list[float], right_values: list[float]) -> float:
    directional_pairs = [
        (left, right)
        for left, right in zip(left_values, right_values, strict=False)
        if abs(left) > FLAT_MOVE_EPSILON and abs(right) > FLAT_MOVE_EPSILON
    ]
    if not directional_pairs:
        return 0.0
    conflicting_count = sum(
        1 for left, right in directional_pairs if signed_direction(left) != signed_direction(right)
    )
    return conflicting_count / len(directional_pairs)


def signed_direction(value: float) -> int:
    if value > FLAT_MOVE_EPSILON:
        return 1
    if value < -FLAT_MOVE_EPSILON:
        return -1
    return 0


def label_alignment(
    correlation_score: Decimal,
    alignment_ratio: float,
    conflict_ratio: float,
    divergence_score: Decimal,
    alignment_threshold: Decimal,
    divergence_threshold: Decimal,
) -> CrossAssetAlignmentLabel:
    if divergence_score >= divergence_threshold:
        return CrossAssetAlignmentLabel.DIVERGENT
    if (
        correlation_score <= -alignment_threshold
        or Decimal(str(conflict_ratio)) >= alignment_threshold
    ):
        return CrossAssetAlignmentLabel.CONFLICTING
    if (
        correlation_score >= alignment_threshold
        and Decimal(str(alignment_ratio)) >= alignment_threshold
    ):
        return CrossAssetAlignmentLabel.ALIGNED
    return CrossAssetAlignmentLabel.PARTIALLY_ALIGNED


def lead_lag_relationship(
    aligned: list[tuple[float, float]],
    max_offset: int,
    min_candles: int,
    relationship_threshold: Decimal,
) -> LeadLagCalculation:
    minimum_overlap = max(min_candles, MIN_LEAD_LAG_OVERLAP)
    candidates: list[dict[str, object]] = []
    best_offset: int | None = None
    best_correlation = 0.0
    for offset in range(-max_offset, max_offset + 1):
        left_values, right_values = offset_values(aligned, offset)
        if len(left_values) < minimum_overlap:
            continue
        correlation = pearson_correlation(left_values, right_values)
        candidates.append(
            {
                "offsetCandles": offset,
                "correlationScore": str(quantize_score(correlation)),
                "overlapCandleCount": len(left_values),
            }
        )
        if abs(correlation) > abs(best_correlation):
            best_offset = offset
            best_correlation = correlation
    if best_offset is None:
        return LeadLagCalculation(None, CrossAssetLeadLagLabel.INSUFFICIENT_DATA, candidates)
    if Decimal(str(abs(best_correlation))) < relationship_threshold:
        return LeadLagCalculation(None, CrossAssetLeadLagLabel.NO_CLEAR_RELATIONSHIP, candidates)
    if best_offset > 0:
        return LeadLagCalculation(best_offset, CrossAssetLeadLagLabel.BASE_LEADS, candidates)
    if best_offset < 0:
        return LeadLagCalculation(best_offset, CrossAssetLeadLagLabel.COMPARED_LEADS, candidates)
    return LeadLagCalculation(0, CrossAssetLeadLagLabel.SYNCHRONOUS, candidates)


def offset_values(
    aligned: list[tuple[float, float]],
    offset: int,
) -> tuple[list[float], list[float]]:
    if offset > 0:
        pairs = aligned[:-offset]
        shifted = aligned[offset:]
        return [pair[0] for pair in pairs], [pair[1] for pair in shifted]
    if offset < 0:
        shift = abs(offset)
        pairs = aligned[shift:]
        shifted = aligned[:-shift]
        return [pair[0] for pair in pairs], [pair[1] for pair in shifted]
    return [pair[0] for pair in aligned], [pair[1] for pair in aligned]


def data_quality(
    overlap_count: int,
    base_count: int,
    compared_count: int,
    min_candles: int,
) -> CrossAssetDataQualityLabel:
    if overlap_count < min_candles:
        return CrossAssetDataQualityLabel.INSUFFICIENT_DATA
    denominator = max(base_count, compared_count, 1)
    coverage = overlap_count / denominator
    if coverage >= 0.90:
        return CrossAssetDataQualityLabel.STRONG
    if coverage >= 0.75:
        return CrossAssetDataQualityLabel.ACCEPTABLE
    return CrossAssetDataQualityLabel.DEGRADED


def insufficient_metadata(
    payload: CrossAssetCalculationInput,
    overlap_count: int,
    data_quality_label: CrossAssetDataQualityLabel,
) -> dict[str, object]:
    return {
        "baseSymbolId": str(payload.base_symbol_id),
        "comparedSymbolId": str(payload.compared_symbol_id),
        "timeframe": payload.timeframe,
        "overlapCandleCount": overlap_count,
        "baseCandleCount": len(payload.base_candles),
        "comparedCandleCount": len(payload.compared_candles),
        "minimumRequiredCandles": payload.min_candles,
        "dataQualityLabel": data_quality_label.value,
        "method": "normalized_directional_movement_correlation_v1",
        "languagePolicy": {
            "contextOnly": True,
            "noCausation": True,
            "noFinancialAdvice": True,
        },
    }


def quantize_score(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(DECIMAL_SCORE_QUANT, rounding=ROUND_HALF_UP)
