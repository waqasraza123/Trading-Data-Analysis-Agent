from decimal import Decimal
from typing import Any

from app.modules.candles.models import Candle

FOUR_PLACES = Decimal("0.0001")


def build_observation_zones(
    support_resistance: dict[str, Any] | None,
    recent_candles: list[Candle],
) -> list[dict[str, object]]:
    zones: list[dict[str, object]] = []
    if support_resistance:
        confidence = str(support_resistance.get("zone_confidence") or "unknown")
        nearest_zone_keys = (
            ("nearest_support", "support"),
            ("nearest_resistance", "resistance"),
        )
        for key, zone_type in nearest_zone_keys:
            zone = support_resistance.get(key)
            if isinstance(zone, dict):
                zones.append(
                    normalize_zone(
                        zone,
                        zone_type,
                        "nearest",
                        "advanced_features",
                        confidence,
                    )
                )
        for key, zone_type in (("support_zones", "support"), ("resistance_zones", "resistance")):
            raw_zones = support_resistance.get(key)
            if isinstance(raw_zones, list):
                for zone in raw_zones[:3]:
                    if isinstance(zone, dict):
                        normalized = normalize_zone(
                            zone,
                            zone_type,
                            "nearby",
                            "advanced_features",
                            confidence,
                        )
                        if normalized not in zones:
                            zones.append(normalized)
    if recent_candles and not zones:
        zones.extend(range_zones(recent_candles))
    return zones[:8]


def build_target_context_zones(
    directional_bias: str,
    observation_zones: list[dict[str, object]],
    recent_candles: list[Candle],
) -> list[dict[str, object]]:
    if directional_bias == "bullish":
        zones = [zone for zone in observation_zones if zone.get("zoneType") == "resistance"]
    elif directional_bias == "bearish":
        zones = [zone for zone in observation_zones if zone.get("zoneType") == "support"]
    else:
        zones = [zone for zone in observation_zones if zone.get("role") == "nearest"]
    if zones:
        return [
            {
                **zone,
                "role": "target_context",
                "description": "Context zone for observing possible next range behavior",
            }
            for zone in zones[:4]
        ]
    return [
        {
            **zone,
            "role": "target_context",
            "description": "Recent range context for observing possible next range behavior",
        }
        for zone in range_zones(recent_candles)[:2]
    ]


def build_invalidation_context(
    directional_bias: str,
    observation_zones: list[dict[str, object]],
    recent_candles: list[Candle],
) -> list[dict[str, object]]:
    contexts: list[dict[str, object]] = []
    if directional_bias == "bullish":
        contexts.extend(
            invalidation_from_zones(
                observation_zones,
                "support",
                "Bullish context weakens if final candles hold below this context zone",
            )
        )
        contexts.extend(
            range_invalidation(
                recent_candles,
                "recent_range_low",
                "Bullish context weakens if final candles hold below the recent range low",
            )
        )
    elif directional_bias == "bearish":
        contexts.extend(
            invalidation_from_zones(
                observation_zones,
                "resistance",
                "Bearish context weakens if final candles hold above this context zone",
            )
        )
        contexts.extend(
            range_invalidation(
                recent_candles,
                "recent_range_high",
                "Bearish context weakens if final candles hold above the recent range high",
            )
        )
    else:
        contexts.extend(
            invalidation_from_zones(
                observation_zones,
                "support",
                "Neutral context requires review if final candles hold beyond this support context",
            )
        )
        contexts.extend(
            invalidation_from_zones(
                observation_zones,
                "resistance",
                (
                    "Neutral context requires review if final candles hold beyond "
                    "this resistance context"
                ),
            )
        )
    return contexts[:4]


def invalidation_from_zones(
    zones: list[dict[str, object]],
    zone_type: str,
    condition: str,
) -> list[dict[str, object]]:
    return [
        {
            "contextType": "invalidation_context",
            "zoneType": zone_type,
            "lower": zone.get("lower"),
            "upper": zone.get("upper"),
            "midpoint": zone.get("midpoint"),
            "source": zone.get("source"),
            "confidence": zone.get("confidence"),
            "condition": condition,
        }
        for zone in zones
        if zone.get("zoneType") == zone_type
    ][:2]


def range_invalidation(
    recent_candles: list[Candle],
    context_type: str,
    condition: str,
) -> list[dict[str, object]]:
    if not recent_candles:
        return []
    low = min(candle.low for candle in recent_candles)
    high = max(candle.high for candle in recent_candles)
    value = low if context_type == "recent_range_low" else high
    return [
        {
            "contextType": "invalidation_context",
            "zoneType": context_type,
            "level": decimal_string(value),
            "source": "recent_final_candle_range",
            "confidence": "observed_range",
            "condition": condition,
        }
    ]


def range_zones(candles: list[Candle]) -> list[dict[str, object]]:
    if not candles:
        return []
    low = min(candle.low for candle in candles)
    high = max(candle.high for candle in candles)
    midpoint = (low + high) / Decimal("2")
    return [
        {
            "zoneType": "support",
            "role": "recent_range",
            "lower": decimal_string(low),
            "upper": decimal_string(midpoint),
            "midpoint": decimal_string((low + midpoint) / Decimal("2")),
            "source": "recent_final_candle_range",
            "confidence": "observed_range",
            "metadata": {"candleCount": len(candles)},
        },
        {
            "zoneType": "resistance",
            "role": "recent_range",
            "lower": decimal_string(midpoint),
            "upper": decimal_string(high),
            "midpoint": decimal_string((midpoint + high) / Decimal("2")),
            "source": "recent_final_candle_range",
            "confidence": "observed_range",
            "metadata": {"candleCount": len(candles)},
        },
    ]


def normalize_zone(
    zone: dict[str, Any],
    zone_type: str,
    role: str,
    source: str,
    confidence: str,
) -> dict[str, object]:
    return {
        "zoneType": zone_type,
        "role": role,
        "lower": str(zone.get("lower")) if zone.get("lower") is not None else None,
        "upper": str(zone.get("upper")) if zone.get("upper") is not None else None,
        "midpoint": str(zone.get("midpoint")) if zone.get("midpoint") is not None else None,
        "source": source,
        "confidence": confidence,
        "metadata": {"touchCount": zone.get("touch_count")},
    }


def decimal_string(value: Decimal) -> str:
    return str(value.quantize(FOUR_PLACES))
