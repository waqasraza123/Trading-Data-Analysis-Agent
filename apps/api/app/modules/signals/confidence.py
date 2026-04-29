from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.patterns.models import PatternCandidate
from app.modules.signals.models import SignalConfidenceLabel

FOUR_PLACES = Decimal("0.0001")
FIVE_PLACES = Decimal("0.00001")


@dataclass(frozen=True)
class ConfidenceComponentScore:
    component_name: str
    component_score: Decimal
    component_weight: Decimal
    weighted_score: Decimal
    reason: str


@dataclass(frozen=True)
class ConfidenceResult:
    confidence_score: Decimal
    confidence_label: SignalConfidenceLabel
    components: tuple[ConfidenceComponentScore, ...]
    risk_notes: tuple[dict[str, object], ...]


def calculate_confidence(
    candidate: PatternCandidate,
    component_weights: Mapping[str, object],
    features: Mapping[str, Any] | None,
    indicators: Mapping[str, Any] | None,
) -> ConfidenceResult:
    risk_notes: list[dict[str, object]] = []
    component_scores = {
        "pattern_strength": pattern_strength_score(candidate),
        "trend_alignment": trend_alignment_score(candidate, features, risk_notes),
        "volatility_confirmation": volatility_confirmation_score(candidate, features, risk_notes),
        "indicator_support": indicator_support_score(candidate, indicators, risk_notes),
        "data_quality": data_quality_score(features, risk_notes),
    }
    components: list[ConfidenceComponentScore] = []
    total_weight = Decimal("0")
    weighted_total = Decimal("0")
    for component_name, component_score in component_scores.items():
        weight = decimal_value(component_weights.get(component_name)) or Decimal("0")
        weighted_score = clamp_score(component_score * weight, FIVE_PLACES)
        total_weight += weight
        weighted_total += weighted_score
        components.append(
            ConfidenceComponentScore(
                component_name=component_name,
                component_score=clamp_score(component_score),
                component_weight=clamp_score(weight),
                weighted_score=weighted_score,
                reason=component_reason(component_name, candidate, features, indicators),
            )
        )
    confidence_score = Decimal("0.0000")
    if total_weight > 0:
        confidence_score = clamp_score(weighted_total / total_weight)
    return ConfidenceResult(
        confidence_score=confidence_score,
        confidence_label=confidence_label(confidence_score),
        components=tuple(components),
        risk_notes=tuple(risk_notes),
    )


def pattern_strength_score(candidate: PatternCandidate) -> Decimal:
    return clamp_score(candidate.strength_score)


def trend_alignment_score(
    candidate: PatternCandidate,
    features: Mapping[str, Any] | None,
    risk_notes: list[dict[str, object]],
) -> Decimal:
    trend_state = string_feature(features, "trend", "trendState")
    if trend_state is None:
        risk_notes.append(missing_snapshot_note("missing_feature_snapshot", "trend features"))
        return Decimal("0.5000")
    if candidate.bias == "bullish":
        if trend_state == "short_term_uptrend":
            return Decimal("1.0000")
        if trend_state == "mixed_or_sideways":
            return Decimal("0.5500")
        return Decimal("0.1500")
    if candidate.bias == "bearish":
        if trend_state == "short_term_downtrend":
            return Decimal("1.0000")
        if trend_state == "mixed_or_sideways":
            return Decimal("0.5500")
        return Decimal("0.1500")
    return Decimal("1.0000") if trend_state == "mixed_or_sideways" else Decimal("0.6500")


def volatility_confirmation_score(
    candidate: PatternCandidate,
    features: Mapping[str, Any] | None,
    risk_notes: list[dict[str, object]],
) -> Decimal:
    volatility_state = string_feature(features, "volatility", "volatilityState")
    if volatility_state is None:
        risk_notes.append(missing_snapshot_note("missing_feature_snapshot", "volatility features"))
        return Decimal("0.5000")
    if candidate.pattern_type in {"sideways_range", "low_volatility_chop", "unclear_structure"}:
        return {
            "compressed": Decimal("1.0000"),
            "normal": Decimal("0.7500"),
            "unknown": Decimal("0.5000"),
            "expanding": Decimal("0.3000"),
            "spike": Decimal("0.2000"),
        }.get(volatility_state, Decimal("0.5000"))
    if candidate.pattern_type == "fakeout":
        return {
            "compressed": Decimal("0.8000"),
            "normal": Decimal("0.8500"),
            "expanding": Decimal("0.6500"),
            "spike": Decimal("0.5500"),
            "unknown": Decimal("0.5000"),
        }.get(volatility_state, Decimal("0.5000"))
    return {
        "compressed": Decimal("0.2000"),
        "normal": Decimal("0.8000"),
        "expanding": Decimal("1.0000"),
        "spike": Decimal("0.7000"),
        "unknown": Decimal("0.5000"),
    }.get(volatility_state, Decimal("0.5000"))


def indicator_support_score(
    candidate: PatternCandidate,
    indicators: Mapping[str, Any] | None,
    risk_notes: list[dict[str, object]],
) -> Decimal:
    if indicators is None:
        risk_notes.append(missing_snapshot_note("missing_indicator_snapshot", "indicator snapshot"))
        return Decimal("0.5000")
    ema_alignment = nested_string(indicators, "ema", "alignment")
    rsi_state_value = nested_string(indicators, "rsi", "state")
    macd_state_value = nested_string(indicators, "macd", "state")
    if candidate.bias == "bullish":
        return average_known_scores(
            (
                directional_score(ema_alignment, "bullish_alignment", "bearish_alignment"),
                directional_score(rsi_state_value, "bullish_momentum", "bearish_momentum"),
                directional_score(macd_state_value, "bullish", "bearish"),
            )
        )
    if candidate.bias == "bearish":
        return average_known_scores(
            (
                directional_score(ema_alignment, "bearish_alignment", "bullish_alignment"),
                directional_score(rsi_state_value, "bearish_momentum", "bullish_momentum"),
                directional_score(macd_state_value, "bearish", "bullish"),
            )
        )
    return average_known_scores(
        (
            neutral_score(ema_alignment, "mixed"),
            neutral_score(rsi_state_value, "neutral"),
            neutral_score(macd_state_value, "neutral"),
        )
    )


def data_quality_score(
    features: Mapping[str, Any] | None,
    risk_notes: list[dict[str, object]],
) -> Decimal:
    score = decimal_feature(features, "dataQuality", "qualityScore")
    if score is None:
        risk_notes.append(missing_snapshot_note("missing_feature_snapshot", "data quality"))
        return Decimal("0.5000")
    return clamp_score(score)


def component_reason(
    component_name: str,
    candidate: PatternCandidate,
    features: Mapping[str, Any] | None,
    indicators: Mapping[str, Any] | None,
) -> str:
    if component_name == "pattern_strength":
        return "Selected candidate strength."
    if component_name == "trend_alignment":
        return f"Trend state evaluated against {candidate.bias} candidate bias."
    if component_name == "volatility_confirmation":
        return "Volatility state evaluated against selected pattern behavior."
    if component_name == "indicator_support":
        return "EMA, RSI, and MACD state evaluated as supporting indicators."
    if component_name == "data_quality":
        return "Candle quality score from the feature snapshot."
    return "Deterministic confidence component."


def confidence_label(score: Decimal) -> SignalConfidenceLabel:
    if score < Decimal("0.5000"):
        return SignalConfidenceLabel.LOW
    if score < Decimal("0.7000"):
        return SignalConfidenceLabel.MEDIUM
    if score < Decimal("0.8500"):
        return SignalConfidenceLabel.HIGH
    return SignalConfidenceLabel.VERY_HIGH


def average_known_scores(scores: tuple[Decimal | None, ...]) -> Decimal:
    known_scores = [score for score in scores if score is not None]
    if not known_scores:
        return Decimal("0.5000")
    return clamp_score(sum(known_scores, Decimal("0")) / Decimal(len(known_scores)))


def directional_score(value: str | None, supportive: str, contradictory: str) -> Decimal | None:
    if value is None or value == "unknown":
        return None
    if value == supportive:
        return Decimal("1.0000")
    if value == contradictory:
        return Decimal("0.1500")
    return Decimal("0.5500")


def neutral_score(value: str | None, neutral_value: str) -> Decimal | None:
    if value is None or value == "unknown":
        return None
    if value == neutral_value:
        return Decimal("1.0000")
    return Decimal("0.5500")


def string_feature(
    values: Mapping[str, Any] | None,
    section: str,
    key: str,
) -> str | None:
    item = mapping_feature(values, section).get(key)
    return item if isinstance(item, str) else None


def decimal_feature(
    values: Mapping[str, Any] | None,
    section: str,
    key: str,
) -> Decimal | None:
    return decimal_value(mapping_feature(values, section).get(key))


def mapping_feature(values: Mapping[str, Any] | None, key: str) -> Mapping[str, Any]:
    if values is None:
        return {}
    item = values.get(key)
    if isinstance(item, Mapping):
        return item
    return {}


def nested_string(values: Mapping[str, Any], section: str, key: str) -> str | None:
    item = mapping_feature(values, section).get(key)
    return item if isinstance(item, str) else None


def decimal_value(value: object) -> Decimal | None:
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


def clamp_score(value: Decimal, quantizer: Decimal = FOUR_PLACES) -> Decimal:
    if value < 0:
        return Decimal("0").quantize(quantizer)
    if value > 1:
        return Decimal("1").quantize(quantizer)
    return value.quantize(quantizer)


def missing_snapshot_note(code: str, item: str) -> dict[str, object]:
    return {
        "code": code,
        "message": f"Missing {item}; confidence component used degraded neutral score.",
        "severity": "medium",
    }
