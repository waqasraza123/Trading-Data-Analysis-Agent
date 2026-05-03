from decimal import Decimal

from app.modules.candles.models import Candle

ZERO = Decimal("0")
FOUR_PLACES = Decimal("0.0001")


def calculate_support_resistance_zones(
    candles: list[Candle],
    zone_lookback: int,
) -> dict[str, object]:
    recent = candles[-zone_lookback:] if len(candles) > zone_lookback else candles
    if not recent:
        return {
            "support_zones": [],
            "resistance_zones": [],
            "nearest_support": None,
            "nearest_resistance": None,
            "zone_confidence": "0.0000",
        }
    current_price = recent[-1].close
    tolerance = zone_tolerance(recent)
    support_zones = [
        zone
        for zone in build_zones([candle.low for candle in recent], tolerance)
        if Decimal(str(zone["midpoint"])) <= current_price
    ]
    resistance_zones = [
        zone
        for zone in build_zones([candle.high for candle in recent], tolerance)
        if Decimal(str(zone["midpoint"])) >= current_price
    ]
    nearest_support = nearest_zone(support_zones, current_price)
    nearest_resistance = nearest_zone(resistance_zones, current_price)
    confidence = max(
        [zone_confidence(support_zones), zone_confidence(resistance_zones)],
        default=ZERO,
    )
    return {
        "support_zones": support_zones,
        "resistance_zones": resistance_zones,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "zone_confidence": decimal_string(confidence),
    }


def build_zones(prices: list[Decimal], tolerance: Decimal) -> list[dict[str, object]]:
    zones: list[list[Decimal]] = []
    for price in sorted(prices):
        matching_zone = next(
            (zone for zone in zones if abs(price - average(zone)) <= tolerance),
            None,
        )
        if matching_zone is None:
            zones.append([price])
        else:
            matching_zone.append(price)
    return [
        {
            "lower": str(min(zone)),
            "upper": str(max(zone)),
            "midpoint": str(average(zone)),
            "touch_count": len(zone),
        }
        for zone in zones
        if len(zone) >= 2
    ]


def nearest_zone(
    zones: list[dict[str, object]],
    current_price: Decimal,
) -> dict[str, object] | None:
    if not zones:
        return None
    return min(
        zones,
        key=lambda zone: abs(Decimal(str(zone["midpoint"])) - current_price),
    )


def zone_confidence(zones: list[dict[str, object]]) -> Decimal:
    if not zones:
        return ZERO
    strongest_touch_count = max(int(zone["touch_count"]) for zone in zones)
    return min(Decimal("1"), Decimal(strongest_touch_count) / Decimal("5"))


def zone_tolerance(candles: list[Candle]) -> Decimal:
    average_range = average([candle.high - candle.low for candle in candles])
    current_price = candles[-1].close
    price_floor = current_price * Decimal("0.001")
    return max(average_range * Decimal("0.35"), price_floor)


def average(values: list[Decimal]) -> Decimal:
    if not values:
        return ZERO
    return sum(values, ZERO) / Decimal(len(values))


def decimal_string(value: Decimal) -> str:
    return str(value.quantize(FOUR_PLACES))
