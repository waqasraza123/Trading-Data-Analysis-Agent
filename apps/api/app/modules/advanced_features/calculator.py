from dataclasses import dataclass
from decimal import Decimal

from app.modules.advanced_features.pressure import (
    calculate_wick_pressure,
    lower_wick_ratio,
    upper_wick_ratio,
)
from app.modules.advanced_features.swing_structure import calculate_swing_structure
from app.modules.advanced_features.zones import calculate_support_resistance_zones
from app.modules.candles.models import Candle
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.symbols.models import Symbol

ZERO = Decimal("0")
ONE = Decimal("1")
FOUR_PLACES = Decimal("0.0001")


@dataclass(frozen=True)
class AdvancedFeatureCalculatorSettings:
    min_candle_count: int
    swing_lookback: int
    zone_lookback: int
    compression_lookback: int
    expansion_multiplier: Decimal
    wick_pressure_threshold: Decimal
    movement_efficiency_threshold: Decimal


@dataclass(frozen=True)
class AdvancedFeatureCalculationInput:
    candles: list[Candle]
    symbol: Symbol
    feature_snapshot: FeatureSnapshot | None
    indicator_snapshot: IndicatorSnapshot | None
    settings: AdvancedFeatureCalculatorSettings
    feature_pack_version: str


@dataclass(frozen=True)
class AdvancedFeatureCalculation:
    impulse_json: dict[str, object]
    correction_json: dict[str, object]
    wick_pressure_json: dict[str, object]
    movement_efficiency_json: dict[str, object]
    compression_expansion_json: dict[str, object]
    swing_structure_json: dict[str, object]
    support_resistance_json: dict[str, object]
    exhaustion_json: dict[str, object]
    liquidity_sweep_json: dict[str, object]
    warnings_json: dict[str, object]
    summary: str


class AdvancedFeatureCalculator:
    def calculate(self, payload: AdvancedFeatureCalculationInput) -> AdvancedFeatureCalculation:
        candles = payload.candles
        warnings = self.warnings(payload)
        if len(candles) < payload.settings.min_candle_count:
            warnings.append(
                "Advanced feature pack expected at least "
                f"{payload.settings.min_candle_count} final candles"
            )
        impulse = self.calculate_impulse(candles, payload.settings)
        correction = self.calculate_correction(candles)
        wick_pressure = calculate_wick_pressure(
            candles,
            payload.settings.wick_pressure_threshold,
        )
        movement_efficiency = self.calculate_movement_efficiency(candles, payload.settings)
        compression_expansion = self.calculate_compression_expansion(candles, payload.settings)
        swing_structure = calculate_swing_structure(candles, payload.settings.swing_lookback)
        support_resistance = calculate_support_resistance_zones(
            candles,
            payload.settings.zone_lookback,
        )
        exhaustion = self.calculate_exhaustion(candles, payload.settings)
        liquidity_sweep = self.calculate_liquidity_sweep(candles, payload.settings)
        return AdvancedFeatureCalculation(
            impulse_json=impulse,
            correction_json=correction,
            wick_pressure_json=wick_pressure,
            movement_efficiency_json=movement_efficiency,
            compression_expansion_json=compression_expansion,
            swing_structure_json=swing_structure,
            support_resistance_json=support_resistance,
            exhaustion_json=exhaustion,
            liquidity_sweep_json=liquidity_sweep,
            warnings_json={"warnings": warnings},
            summary=self.summary(
                impulse=impulse,
                movement_efficiency=movement_efficiency,
                compression_expansion=compression_expansion,
                swing_structure=swing_structure,
                wick_pressure=wick_pressure,
                liquidity_sweep=liquidity_sweep,
            ),
        )

    def calculate_impulse(
        self,
        candles: list[Candle],
        settings: AdvancedFeatureCalculatorSettings,
    ) -> dict[str, object]:
        if not candles:
            return {
                "impulse_direction": "unclear",
                "large_body_count": 0,
                "consecutive_direction_count": 0,
                "average_body_to_range_ratio": "0.0000",
                "impulse_score": "0.0000",
            }
        body_ratios = [body_to_range_ratio(candle) for candle in candles]
        directions = [candle_direction(candle) for candle in candles]
        large_body_count = sum(
            1 for ratio in body_ratios if ratio >= settings.movement_efficiency_threshold
        )
        consecutive_direction_count = longest_direction_sequence(directions)
        average_body_ratio = average(body_ratios)
        efficiency = efficiency_score(candles)
        impulse_score = clamp(
            (
                Decimal(large_body_count) / Decimal(len(candles))
                + Decimal(consecutive_direction_count) / Decimal(len(candles))
                + average_body_ratio
                + efficiency
            )
            / Decimal("4")
        )
        return {
            "impulse_direction": impulse_direction(candles, directions, impulse_score),
            "large_body_count": large_body_count,
            "consecutive_direction_count": consecutive_direction_count,
            "average_body_to_range_ratio": decimal_string(average_body_ratio),
            "impulse_score": decimal_string(impulse_score),
        }

    def calculate_correction(self, candles: list[Candle]) -> dict[str, object]:
        if len(candles) < 2:
            return {
                "pullback_count": 0,
                "average_pullback_depth": "0.0000",
                "pullback_against_primary_direction": False,
                "correction_score": "0.0000",
            }
        primary_direction = net_direction(candles)
        pullback_bodies = [
            body_size(candle)
            for candle in candles
            if primary_direction != 0 and candle_direction(candle) == -primary_direction
        ]
        gross_body = sum((body_size(candle) for candle in candles), ZERO)
        average_pullback_depth = (
            average(pullback_bodies) / gross_body if gross_body > ZERO and pullback_bodies else ZERO
        )
        correction_score = clamp(
            (Decimal(len(pullback_bodies)) / Decimal(len(candles)) * Decimal("0.6"))
            + min(Decimal("0.4"), average_pullback_depth)
        )
        return {
            "pullback_count": len(pullback_bodies),
            "average_pullback_depth": decimal_string(clamp(average_pullback_depth)),
            "pullback_against_primary_direction": bool(pullback_bodies),
            "correction_score": decimal_string(correction_score),
        }

    def calculate_movement_efficiency(
        self,
        candles: list[Candle],
        settings: AdvancedFeatureCalculatorSettings,
    ) -> dict[str, object]:
        if len(candles) < 2:
            return {
                "net_move": "0",
                "gross_movement": "0",
                "efficiency_score": "0.0000",
                "efficiency_label": "unclear",
            }
        net_move = candles[-1].close - candles[0].open
        gross_movement = sum(
            (
                abs(current.close - previous.close)
                for previous, current in zip(candles, candles[1:], strict=False)
            ),
            ZERO,
        )
        score = abs(net_move) / gross_movement if gross_movement > ZERO else ZERO
        return {
            "net_move": str(net_move),
            "gross_movement": str(gross_movement),
            "efficiency_score": decimal_string(clamp(score)),
            "efficiency_label": efficiency_label(score, settings.movement_efficiency_threshold),
        }

    def calculate_compression_expansion(
        self,
        candles: list[Candle],
        settings: AdvancedFeatureCalculatorSettings,
    ) -> dict[str, object]:
        lookback_candles = candles[-settings.compression_lookback :]
        if len(lookback_candles) < 4:
            return {
                "compression_detected": False,
                "expansion_detected": False,
                "compression_range": "0",
                "expansion_range": "0",
                "expansion_ratio": "0.0000",
                "label": "unclear",
            }
        split_index = len(lookback_candles) // 2
        compression_window = lookback_candles[:split_index]
        expansion_window = lookback_candles[split_index:]
        compression_average = average_candle_range(compression_window)
        expansion_average = average_candle_range(expansion_window)
        all_average = average_candle_range(lookback_candles)
        expansion_ratio = (
            expansion_average / compression_average if compression_average > ZERO else ZERO
        )
        compression_detected = compression_average <= all_average * Decimal("0.75")
        expansion_detected = expansion_ratio >= settings.expansion_multiplier
        return {
            "compression_detected": compression_detected,
            "expansion_detected": expansion_detected,
            "compression_range": str(window_range(compression_window)),
            "expansion_range": str(window_range(expansion_window)),
            "expansion_ratio": decimal_string(expansion_ratio),
            "label": compression_expansion_label(compression_detected, expansion_detected),
        }

    def calculate_exhaustion(
        self,
        candles: list[Candle],
        settings: AdvancedFeatureCalculatorSettings,
    ) -> dict[str, object]:
        if len(candles) < 3:
            return {
                "body_expansion_then_wick_rejection": False,
                "decreasing_body_sequence": False,
                "exhaustion_direction": "none",
                "exhaustion_score": "0.0000",
            }
        recent = candles[-3:]
        bodies = [body_size(candle) for candle in recent]
        last = recent[-1]
        upper_rejection = upper_wick_ratio(last) >= settings.wick_pressure_threshold
        lower_rejection = lower_wick_ratio(last) >= settings.wick_pressure_threshold
        body_expansion_then_wick_rejection = bodies[0] < bodies[1] <= bodies[2] and (
            upper_rejection or lower_rejection
        )
        decreasing_body_sequence = bodies[0] > bodies[1] > bodies[2]
        direction = exhaustion_direction(upper_rejection, lower_rejection)
        score = clamp(
            (Decimal("0.45") if body_expansion_then_wick_rejection else ZERO)
            + (Decimal("0.25") if decreasing_body_sequence else ZERO)
            + max(upper_wick_ratio(last), lower_wick_ratio(last)) * Decimal("0.30")
        )
        return {
            "body_expansion_then_wick_rejection": body_expansion_then_wick_rejection,
            "decreasing_body_sequence": decreasing_body_sequence,
            "exhaustion_direction": direction,
            "exhaustion_score": decimal_string(score),
        }

    def calculate_liquidity_sweep(
        self,
        candles: list[Candle],
        settings: AdvancedFeatureCalculatorSettings,
    ) -> dict[str, object]:
        if len(candles) < 5:
            return {
                "sweep_above_recent_high": False,
                "sweep_below_recent_low": False,
                "failed_hold_after_sweep": False,
                "sweep_direction": "none",
                "sweep_score": "0.0000",
            }
        recent = candles[-min(settings.zone_lookback, len(candles)) : -1]
        last = candles[-1]
        recent_high = max(candle.high for candle in recent)
        recent_low = min(candle.low for candle in recent)
        sweep_above = last.high > recent_high and last.close <= recent_high
        sweep_below = last.low < recent_low and last.close >= recent_low
        failed_hold = sweep_above or sweep_below
        wick_score = max(upper_wick_ratio(last), lower_wick_ratio(last))
        score = clamp((Decimal("0.65") if failed_hold else ZERO) + wick_score * Decimal("0.35"))
        return {
            "sweep_above_recent_high": sweep_above,
            "sweep_below_recent_low": sweep_below,
            "failed_hold_after_sweep": failed_hold,
            "sweep_direction": sweep_direction(sweep_above, sweep_below),
            "sweep_score": decimal_string(score),
        }

    def warnings(self, payload: AdvancedFeatureCalculationInput) -> list[str]:
        warnings: list[str] = []
        if payload.feature_snapshot is None:
            warnings.append("Existing feature snapshot was not available")
        if payload.indicator_snapshot is None:
            warnings.append("Existing indicator snapshot was not available")
        if payload.symbol.pip_size is None and payload.symbol.tick_size is None:
            warnings.append("Symbol pip and tick metadata were not configured")
        return warnings

    def summary(
        self,
        impulse: dict[str, object],
        movement_efficiency: dict[str, object],
        compression_expansion: dict[str, object],
        swing_structure: dict[str, object],
        wick_pressure: dict[str, object],
        liquidity_sweep: dict[str, object],
    ) -> str:
        return (
            "Advanced price action context: "
            f"{impulse['impulse_direction']} impulse, "
            f"{movement_efficiency['efficiency_label']} movement efficiency, "
            f"{compression_expansion['label']} compression/expansion, "
            f"{swing_structure['structure_label']} swing structure, "
            f"{wick_pressure['rejection_direction']} wick rejection, "
            f"{liquidity_sweep['sweep_direction']} liquidity sweep candidate."
        )


def body_size(candle: Candle) -> Decimal:
    return abs(candle.close - candle.open)


def body_to_range_ratio(candle: Candle) -> Decimal:
    candle_range = candle.high - candle.low
    if candle_range <= ZERO:
        return ZERO
    return clamp(body_size(candle) / candle_range)


def candle_direction(candle: Candle) -> int:
    if candle.close > candle.open:
        return 1
    if candle.close < candle.open:
        return -1
    return 0


def net_direction(candles: list[Candle]) -> int:
    if not candles:
        return 0
    if candles[-1].close > candles[0].open:
        return 1
    if candles[-1].close < candles[0].open:
        return -1
    return 0


def impulse_direction(candles: list[Candle], directions: list[int], impulse_score: Decimal) -> str:
    if impulse_score < Decimal("0.25"):
        return "unclear"
    positive_count = sum(1 for direction in directions if direction > 0)
    negative_count = sum(1 for direction in directions if direction < 0)
    net = net_direction(candles)
    if net > 0 and positive_count > negative_count:
        return "bullish"
    if net < 0 and negative_count > positive_count:
        return "bearish"
    if positive_count and negative_count:
        return "mixed"
    return "unclear"


def longest_direction_sequence(directions: list[int]) -> int:
    longest = 0
    current_count = 0
    current_direction = 0
    for direction in directions:
        if direction == 0:
            current_count = 0
            current_direction = 0
            continue
        if direction == current_direction:
            current_count += 1
        else:
            current_direction = direction
            current_count = 1
        longest = max(longest, current_count)
    return longest


def efficiency_score(candles: list[Candle]) -> Decimal:
    if len(candles) < 2:
        return ZERO
    net_move = candles[-1].close - candles[0].open
    gross_movement = sum(
        (
            abs(current.close - previous.close)
            for previous, current in zip(candles, candles[1:], strict=False)
        ),
        ZERO,
    )
    return clamp(abs(net_move) / gross_movement) if gross_movement > ZERO else ZERO


def average(values: list[Decimal]) -> Decimal:
    if not values:
        return ZERO
    return sum(values, ZERO) / Decimal(len(values))


def average_candle_range(candles: list[Candle]) -> Decimal:
    return average([candle.high - candle.low for candle in candles])


def window_range(candles: list[Candle]) -> Decimal:
    if not candles:
        return ZERO
    return max(candle.high for candle in candles) - min(candle.low for candle in candles)


def efficiency_label(score: Decimal, threshold: Decimal) -> str:
    if score >= threshold:
        return "efficient"
    if score >= threshold / Decimal("2"):
        return "moderate"
    if score > ZERO:
        return "choppy"
    return "unclear"


def compression_expansion_label(compression_detected: bool, expansion_detected: bool) -> str:
    if compression_detected and expansion_detected:
        return "compressed_then_expanded"
    if compression_detected:
        return "compressed"
    if expansion_detected:
        return "expanding"
    return "normal"


def exhaustion_direction(upper_rejection: bool, lower_rejection: bool) -> str:
    if upper_rejection and lower_rejection:
        return "mixed"
    if upper_rejection:
        return "bearish"
    if lower_rejection:
        return "bullish"
    return "none"


def sweep_direction(sweep_above: bool, sweep_below: bool) -> str:
    if sweep_above and sweep_below:
        return "mixed"
    if sweep_above:
        return "bearish"
    if sweep_below:
        return "bullish"
    return "none"


def clamp(value: Decimal) -> Decimal:
    return max(ZERO, min(ONE, value))


def decimal_string(value: Decimal) -> str:
    return str(value.quantize(FOUR_PLACES))


def safe_json(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): safe_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe_json(item) for item in value]
    return value
