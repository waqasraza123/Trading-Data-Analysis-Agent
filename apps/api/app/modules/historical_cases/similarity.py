from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


CASE_SIMILARITY_VERSION = "v1"


@dataclass(frozen=True)
class CaseSimilarityResult:
    score: Decimal
    matched_reasons: list[str]
    differing_reasons: list[str]


def build_case_vector(
    signal_summary: dict[str, object],
    feature_summary: dict[str, object],
    indicator_summary: dict[str, object],
    outcome_summary: dict[str, object] | None,
    news_summary: dict[str, object],
    symbol_summary: dict[str, object],
    vector_version: str,
) -> dict[str, object]:
    confidence_score = decimal_or_none(signal_summary.get("confidenceScore"))
    confidence_label = string_or_none(signal_summary.get("confidenceLabel"))
    return {
        "version": vector_version,
        "signal": {
            "bias": string_or_none(signal_summary.get("bias")),
            "classificationStatus": string_or_none(signal_summary.get("classificationStatus")),
            "patternType": string_or_none(signal_summary.get("patternType")),
            "strategyProfileKey": string_or_none(signal_summary.get("strategyProfileKey")),
            "strategyProfileVersion": string_or_none(signal_summary.get("strategyProfileVersion")),
            "confidenceScore": str(confidence_score) if confidence_score is not None else None,
            "confidenceLabel": confidence_label,
            "confidenceBucket": confidence_bucket(confidence_score, confidence_label),
            "timeframe": string_or_none(signal_summary.get("timeframe")),
        },
        "symbol": {
            "symbolId": string_or_none(symbol_summary.get("symbolId")),
            "symbol": string_or_none(symbol_summary.get("symbol")),
            "marketType": string_or_none(symbol_summary.get("marketType")),
        },
        "features": feature_summary,
        "indicators": indicator_summary,
        "news": news_summary,
        "outcomes": outcome_summary or {},
    }


def score_similarity(
    source_vector: dict[str, Any],
    candidate_vector: dict[str, Any],
    include_outcomes: bool,
) -> CaseSimilarityResult:
    checks = [
        weighted_match(
            "strategy_profile_key",
            0.18,
            source_vector,
            candidate_vector,
            "signal.strategyProfileKey",
        ),
        weighted_match("pattern_type", 0.18, source_vector, candidate_vector, "signal.patternType"),
        weighted_match("bias", 0.13, source_vector, candidate_vector, "signal.bias"),
        weighted_match("symbol", 0.10, source_vector, candidate_vector, "symbol.symbolId"),
        weighted_match("timeframe", 0.09, source_vector, candidate_vector, "signal.timeframe"),
        weighted_match("market_type", 0.04, source_vector, candidate_vector, "symbol.marketType"),
        weighted_match("volatility_state", 0.08, source_vector, candidate_vector, "features.volatilityState"),
        weighted_match("trend_state", 0.07, source_vector, candidate_vector, "features.trendState"),
        weighted_match("range_state", 0.06, source_vector, candidate_vector, "features.rangeState"),
        weighted_match("confidence_bucket", 0.04, source_vector, candidate_vector, "signal.confidenceBucket"),
        weighted_match("news_correlation_label", 0.03, source_vector, candidate_vector, "news.correlationLabel"),
    ]
    if include_outcomes:
        checks.append(
            weighted_overlap(
                "outcome_labels",
                0.05,
                source_vector,
                candidate_vector,
                "outcomes.outcomeLabels",
            )
        )
    total_weight = sum(
        check.weight
        for check in checks
        if check.source_value is not None or check.candidate_value is not None
    )
    matched_weight = sum(check.score for check in checks)
    if total_weight == 0:
        return CaseSimilarityResult(score=Decimal("0.0000"), matched_reasons=[], differing_reasons=[])
    score = Decimal(str(matched_weight / total_weight)).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )
    matched_reasons = [check.matched_reason for check in checks if check.matched_reason is not None]
    differing_reasons = [check.differing_reason for check in checks if check.differing_reason is not None]
    return CaseSimilarityResult(score=score, matched_reasons=matched_reasons, differing_reasons=differing_reasons)


@dataclass(frozen=True)
class WeightedCheck:
    weight: float
    score: float
    source_value: object
    candidate_value: object
    matched_reason: str | None
    differing_reason: str | None


def weighted_match(
    label: str,
    weight: float,
    source_vector: dict[str, Any],
    candidate_vector: dict[str, Any],
    path: str,
) -> WeightedCheck:
    source_value = value_at_path(source_vector, path)
    candidate_value = value_at_path(candidate_vector, path)
    if source_value is None and candidate_value is None:
        return WeightedCheck(
            weight=weight,
            score=0.0,
            source_value=None,
            candidate_value=None,
            matched_reason=None,
            differing_reason=None,
        )
    if source_value is not None and source_value == candidate_value:
        return WeightedCheck(
            weight=weight,
            score=weight,
            source_value=source_value,
            candidate_value=candidate_value,
            matched_reason=f"same {label}: {source_value}",
            differing_reason=None,
        )
    return WeightedCheck(
        weight=weight,
        score=0.0,
        source_value=source_value,
        candidate_value=candidate_value,
        matched_reason=None,
        differing_reason=f"different {label}: {source_value} vs {candidate_value}",
    )


def weighted_overlap(
    label: str,
    weight: float,
    source_vector: dict[str, Any],
    candidate_vector: dict[str, Any],
    path: str,
) -> WeightedCheck:
    source_values = set(list_value_at_path(source_vector, path))
    candidate_values = set(list_value_at_path(candidate_vector, path))
    if not source_values and not candidate_values:
        return WeightedCheck(
            weight=weight,
            score=0.0,
            source_value=None,
            candidate_value=None,
            matched_reason=None,
            differing_reason=None,
        )
    overlap = source_values & candidate_values
    if overlap:
        score = weight * (len(overlap) / max(len(source_values | candidate_values), 1))
        return WeightedCheck(
            weight=weight,
            score=score,
            source_value=sorted(source_values),
            candidate_value=sorted(candidate_values),
            matched_reason=f"overlapping {label}: {', '.join(sorted(overlap))}",
            differing_reason=None,
        )
    return WeightedCheck(
        weight=weight,
        score=0.0,
        source_value=sorted(source_values),
        candidate_value=sorted(candidate_values),
        matched_reason=None,
        differing_reason=f"different {label}: {sorted(source_values)} vs {sorted(candidate_values)}",
    )


def value_at_path(payload: dict[str, Any], path: str) -> object:
    value: object = payload
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def list_value_at_path(payload: dict[str, Any], path: str) -> list[str]:
    value = value_at_path(payload, path)
    if not isinstance(value, list):
        return []
    return sorted({str(item) for item in value if item is not None})


def confidence_bucket(score: Decimal | None, label: str | None) -> str | None:
    if label in {"low", "medium", "high", "very_high"}:
        return label
    if score is None:
        return None
    if score < Decimal("0.35"):
        return "low"
    if score < Decimal("0.65"):
        return "medium"
    if score < Decimal("0.85"):
        return "high"
    return "very_high"


def string_or_none(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None
