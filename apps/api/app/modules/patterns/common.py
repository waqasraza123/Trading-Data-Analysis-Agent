from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.candles.models import Candle
from app.modules.patterns.serialization import serialize_pattern_list, serialize_pattern_map

MINIMUM_SELECTION_STRENGTH = Decimal("0.3500")
FOUR_PLACES = Decimal("0.0001")


@dataclass(frozen=True)
class PatternCandidateDraft:
    pattern_type: str
    bias: str
    strength_score: Decimal
    evidence: list[dict[str, object]]
    risk_notes: list[dict[str, object]]
    metrics: dict[str, object]
    is_selected: bool = False

    def selected(self) -> "PatternCandidateDraft":
        return PatternCandidateDraft(
            pattern_type=self.pattern_type,
            bias=self.bias,
            strength_score=self.strength_score,
            evidence=self.evidence,
            risk_notes=self.risk_notes,
            metrics=self.metrics,
            is_selected=True,
        )

    def serialized_evidence(self) -> list[dict[str, object]]:
        return serialize_pattern_list(self.evidence)

    def serialized_risk_notes(self) -> list[dict[str, object]]:
        return serialize_pattern_list(self.risk_notes)

    def serialized_metrics(self) -> dict[str, object]:
        return serialize_pattern_map(self.metrics)


@dataclass(frozen=True)
class PatternDetectionContext:
    analysis_candles: list[Candle]
    baseline_candles: list[Candle]
    features: Mapping[str, Any]
    indicators: Mapping[str, Any]


def build_candidate(
    pattern_type: str,
    bias: str,
    evidence: list[dict[str, object]],
    risk_notes: list[dict[str, object]],
    metrics: dict[str, object],
) -> PatternCandidateDraft:
    return PatternCandidateDraft(
        pattern_type=pattern_type,
        bias=bias,
        strength_score=calculate_strength_score(evidence),
        evidence=evidence,
        risk_notes=risk_notes,
        metrics=metrics,
    )


def evidence_item(
    name: str,
    passed: bool,
    value: object,
    threshold: object,
    weight: Decimal,
) -> dict[str, object]:
    return {
        "name": name,
        "passed": passed,
        "value": value,
        "threshold": threshold,
        "weight": weight,
    }


def calculate_strength_score(evidence: list[dict[str, object]]) -> Decimal:
    total_weight = Decimal("0")
    passed_weight = Decimal("0")
    for item in evidence:
        weight = as_decimal(item.get("weight")) or Decimal("0")
        total_weight += weight
        if item.get("passed") is True:
            passed_weight += weight
    if total_weight == 0:
        return Decimal("0.0000")
    return clamp_score(passed_weight / total_weight)


def clamp_score(value: Decimal) -> Decimal:
    if value < 0:
        return Decimal("0.0000")
    if value > 1:
        return Decimal("1.0000")
    return value.quantize(FOUR_PLACES)


def common_risk_notes(context: PatternDetectionContext) -> list[dict[str, object]]:
    notes: list[dict[str, object]] = []
    range_features = mapping_feature(context.features, "range")
    calculation = mapping_feature(context.indicators, "calculation")
    missing_baseline_range = (
        range_features.get("previousRangeHigh") is None
        or range_features.get("previousRangeLow") is None
    )
    if missing_baseline_range:
        notes.append(
            {
                "code": "missing_baseline_range",
                "severity": "high",
                "message": (
                    "Baseline range is unavailable, range-dependent patterns are less reliable"
                ),
            }
        )
    if calculation.get("isReady") is False:
        notes.append(
            {
                "code": "indicator_warmup_incomplete",
                "severity": "medium",
                "message": "One or more indicator groups are not ready",
            }
        )
    if len(context.analysis_candles) < 5:
        notes.append(
            {
                "code": "shallow_analysis_window",
                "severity": "medium",
                "message": "Analysis window has fewer than five candles",
            }
        )
    return notes


def mapping_feature(values: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = values.get(key)
    if isinstance(item, Mapping):
        return item
    return {}


def as_decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float | str):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    return None


def decimal_feature(values: Mapping[str, Any], section: str, key: str) -> Decimal | None:
    return as_decimal(mapping_feature(values, section).get(key))


def string_feature(values: Mapping[str, Any], section: str, key: str) -> str | None:
    item = mapping_feature(values, section).get(key)
    return item if isinstance(item, str) else None


def integer_feature(values: Mapping[str, Any], section: str, key: str) -> int:
    item = mapping_feature(values, section).get(key)
    if isinstance(item, int) and not isinstance(item, bool):
        return item
    if isinstance(item, str) and item.isdigit():
        return int(item)
    return 0


def latest_body_ratio(candle: Candle) -> Decimal:
    return safe_ratio(abs(candle.close - candle.open), candle.high - candle.low)


def latest_upper_wick_ratio(candle: Candle) -> Decimal:
    return safe_ratio(candle.high - max(candle.open, candle.close), candle.high - candle.low)


def latest_lower_wick_ratio(candle: Candle) -> Decimal:
    return safe_ratio(min(candle.open, candle.close) - candle.low, candle.high - candle.low)


def safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return numerator / denominator


def consecutive_closes_above(candles: list[Candle], level: Decimal | None) -> int:
    if level is None:
        return 0
    count = 0
    for candle in reversed(candles):
        if candle.close <= level:
            break
        count += 1
    return count


def consecutive_closes_below(candles: list[Candle], level: Decimal | None) -> int:
    if level is None:
        return 0
    count = 0
    for candle in reversed(candles):
        if candle.close >= level:
            break
        count += 1
    return count


def close_direction_changes(candles: list[Candle]) -> int:
    directions = [
        1 if candle.close > candle.open else -1 if candle.close < candle.open else 0
        for candle in candles
    ]
    non_zero_directions = [direction for direction in directions if direction != 0]
    return sum(
        1
        for previous, current in zip(non_zero_directions, non_zero_directions[1:], strict=False)
        if previous != current
    )


def recent_price_resumed_up(candles: list[Candle]) -> bool:
    if len(candles) < 2:
        return False
    return candles[-1].close > candles[-2].close and candles[-1].close > candles[-1].open


def recent_price_resumed_down(candles: list[Candle]) -> bool:
    if len(candles) < 2:
        return False
    return candles[-1].close < candles[-2].close and candles[-1].close < candles[-1].open


def first_half_direction(candles: list[Candle]) -> str:
    if not candles:
        return "neutral"
    midpoint = max(1, len(candles) // 2)
    move = candles[midpoint - 1].close - candles[0].open
    if move > 0:
        return "bullish"
    if move < 0:
        return "bearish"
    return "neutral"


def selected_candidates(candidates: list[PatternCandidateDraft]) -> list[PatternCandidateDraft]:
    if not candidates:
        return []
    strongest = max(candidates, key=lambda candidate: candidate.strength_score)
    return [
        candidate.selected()
        if candidate.pattern_type == strongest.pattern_type
        and strongest.strength_score >= MINIMUM_SELECTION_STRENGTH
        else candidate
        for candidate in candidates
    ]
