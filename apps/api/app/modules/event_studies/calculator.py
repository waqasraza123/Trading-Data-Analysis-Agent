from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.modules.candles.models import Candle
from app.modules.event_studies.models import (
    EventStudyDataQualityLabel,
    EventStudyDirectionLabel,
    EventStudyReactionLabel,
    EventStudyVolatilityReaction,
)
from app.modules.symbols.models import Symbol

ZERO = Decimal("0")
MARKET_VALUE_QUANT = Decimal("0.0000000001")
NEUTRAL_MOVE_THRESHOLD_RATIO = Decimal("0.10")


@dataclass(frozen=True)
class EventStudyCalculationRequest:
    symbol: Symbol
    timeframe: str
    event_time: datetime
    pre_event_minutes: int
    post_event_minutes: int
    minimum_candles: int
    strong_reaction_multiplier: Decimal
    moderate_reaction_multiplier: Decimal
    pre_candles: list[Candle]
    post_candles: list[Candle]


@dataclass(frozen=True)
class EventStudyCalculation:
    timeframe: str
    event_time: datetime
    pre_window_start: datetime
    pre_window_end: datetime
    post_window_start: datetime
    post_window_end: datetime
    pre_candle_count: int
    post_candle_count: int
    pre_move: Decimal
    post_move: Decimal
    post_move_pips: Decimal | None
    post_move_ticks: Decimal | None
    pre_volatility_json: dict[str, object]
    post_volatility_json: dict[str, object]
    volatility_reaction: EventStudyVolatilityReaction
    direction_label: EventStudyDirectionLabel
    reaction_label: EventStudyReactionLabel
    data_quality_label: EventStudyDataQualityLabel
    metadata_json: dict[str, object]


class EventStudyCalculator:
    def calculate(self, request: EventStudyCalculationRequest) -> EventStudyCalculation:
        pre_window_start = request.event_time - timedelta(minutes=request.pre_event_minutes)
        pre_window_end = request.event_time
        post_window_start = request.event_time
        post_window_end = request.event_time + timedelta(minutes=request.post_event_minutes)
        sorted_pre_candles = sorted(request.pre_candles, key=lambda candle: candle.timestamp)
        sorted_post_candles = sorted(request.post_candles, key=lambda candle: candle.timestamp)
        pre_candle_count = len(sorted_pre_candles)
        post_candle_count = len(sorted_post_candles)
        has_sufficient_data = (
            pre_candle_count >= request.minimum_candles
            and post_candle_count >= request.minimum_candles
        )
        pre_move = calculate_window_move(sorted_pre_candles)
        post_move = calculate_window_move(sorted_post_candles)
        pre_volatility = calculate_volatility_payload(sorted_pre_candles)
        post_volatility = calculate_volatility_payload(sorted_post_candles)
        data_quality_label = data_quality(pre_candle_count, post_candle_count, request.minimum_candles)
        volatility_reaction = label_volatility_reaction(
            pre_average_range=decimal_from_payload(pre_volatility, "averageRange"),
            post_average_range=decimal_from_payload(post_volatility, "averageRange"),
            has_sufficient_data=has_sufficient_data,
            moderate_multiplier=request.moderate_reaction_multiplier,
            strong_multiplier=request.strong_reaction_multiplier,
        )
        direction_label = label_direction(
            pre_move=pre_move,
            post_move=post_move,
            post_average_range=decimal_from_payload(post_volatility, "averageRange"),
            has_sufficient_data=has_sufficient_data,
        )
        reaction_label = label_reaction(
            pre_move=pre_move,
            post_move=post_move,
            pre_average_range=decimal_from_payload(pre_volatility, "averageRange"),
            has_sufficient_data=has_sufficient_data,
            moderate_multiplier=request.moderate_reaction_multiplier,
            strong_multiplier=request.strong_reaction_multiplier,
        )
        return EventStudyCalculation(
            timeframe=request.timeframe,
            event_time=request.event_time,
            pre_window_start=pre_window_start,
            pre_window_end=pre_window_end,
            post_window_start=post_window_start,
            post_window_end=post_window_end,
            pre_candle_count=pre_candle_count,
            post_candle_count=post_candle_count,
            pre_move=quantize_market_value(pre_move),
            post_move=quantize_market_value(post_move),
            post_move_pips=convert_market_units(post_move, request.symbol.pip_size),
            post_move_ticks=convert_market_units(post_move, request.symbol.tick_size),
            pre_volatility_json=pre_volatility,
            post_volatility_json=post_volatility,
            volatility_reaction=volatility_reaction,
            direction_label=direction_label,
            reaction_label=reaction_label,
            data_quality_label=data_quality_label,
            metadata_json={
                "calculationVersion": "event_study_calculator_v1",
                "minimumCandles": request.minimum_candles,
                "strongReactionMultiplier": str(request.strong_reaction_multiplier),
                "moderateReactionMultiplier": str(request.moderate_reaction_multiplier),
                "languagePolicy": {
                    "doesNotClaimCausation": True,
                    "doesNotProvideFinancialAdvice": True,
                    "doesNotMutateSignals": True,
                },
            },
        )


def calculate_window_move(candles: list[Candle]) -> Decimal:
    if not candles:
        return ZERO
    return candles[-1].close - candles[0].open


def calculate_volatility_payload(candles: list[Candle]) -> dict[str, object]:
    if not candles:
        return {
            "candleCount": 0,
            "range": str(ZERO),
            "averageRange": str(ZERO),
            "maxRange": str(ZERO),
            "averageCloseChange": str(ZERO),
            "high": None,
            "low": None,
        }
    candle_ranges = [candle.high - candle.low for candle in candles]
    close_changes = [
        abs(candles[index].close - candles[index - 1].close)
        for index in range(1, len(candles))
    ]
    high = max(candle.high for candle in candles)
    low = min(candle.low for candle in candles)
    return {
        "candleCount": len(candles),
        "range": str(quantize_market_value(high - low)),
        "averageRange": str(quantize_market_value(sum(candle_ranges, ZERO) / len(candle_ranges))),
        "maxRange": str(quantize_market_value(max(candle_ranges))),
        "averageCloseChange": str(
            quantize_market_value(
                sum(close_changes, ZERO) / len(close_changes) if close_changes else ZERO
            )
        ),
        "high": str(quantize_market_value(high)),
        "low": str(quantize_market_value(low)),
    }


def label_volatility_reaction(
    pre_average_range: Decimal,
    post_average_range: Decimal,
    has_sufficient_data: bool,
    moderate_multiplier: Decimal,
    strong_multiplier: Decimal,
) -> EventStudyVolatilityReaction:
    if not has_sufficient_data:
        return EventStudyVolatilityReaction.INSUFFICIENT_DATA
    if post_average_range <= ZERO:
        return EventStudyVolatilityReaction.NONE
    if pre_average_range <= ZERO:
        return EventStudyVolatilityReaction.ELEVATED
    ratio = post_average_range / pre_average_range
    if ratio >= strong_multiplier:
        return EventStudyVolatilityReaction.SPIKE
    if ratio >= moderate_multiplier:
        return EventStudyVolatilityReaction.ELEVATED
    return EventStudyVolatilityReaction.NORMAL


def label_direction(
    pre_move: Decimal,
    post_move: Decimal,
    post_average_range: Decimal,
    has_sufficient_data: bool,
) -> EventStudyDirectionLabel:
    if not has_sufficient_data:
        return EventStudyDirectionLabel.INSUFFICIENT_DATA
    neutral_threshold = post_average_range * NEUTRAL_MOVE_THRESHOLD_RATIO
    if abs(post_move) <= neutral_threshold:
        return EventStudyDirectionLabel.NEUTRAL
    if pre_move != ZERO and post_move != ZERO and sign(pre_move) != sign(post_move):
        return EventStudyDirectionLabel.MIXED
    if post_move > ZERO:
        return EventStudyDirectionLabel.BULLISH
    return EventStudyDirectionLabel.BEARISH


def label_reaction(
    pre_move: Decimal,
    post_move: Decimal,
    pre_average_range: Decimal,
    has_sufficient_data: bool,
    moderate_multiplier: Decimal,
    strong_multiplier: Decimal,
) -> EventStudyReactionLabel:
    if not has_sufficient_data:
        return EventStudyReactionLabel.INSUFFICIENT_DATA
    observed_move = abs(post_move)
    if observed_move == ZERO:
        return EventStudyReactionLabel.NO_CLEAR_REACTION
    baseline = max(abs(pre_move), pre_average_range)
    if baseline <= ZERO:
        return EventStudyReactionLabel.WEAK_REACTION
    ratio = observed_move / baseline
    if ratio >= strong_multiplier:
        return EventStudyReactionLabel.STRONG_REACTION
    if ratio >= moderate_multiplier:
        return EventStudyReactionLabel.MODERATE_REACTION
    return EventStudyReactionLabel.WEAK_REACTION


def data_quality(
    pre_candle_count: int,
    post_candle_count: int,
    minimum_candles: int,
) -> EventStudyDataQualityLabel:
    if pre_candle_count >= minimum_candles and post_candle_count >= minimum_candles:
        return EventStudyDataQualityLabel.COMPLETE
    if pre_candle_count == 0 or post_candle_count == 0:
        return EventStudyDataQualityLabel.INSUFFICIENT_DATA
    return EventStudyDataQualityLabel.PARTIAL


def convert_market_units(value: Decimal, unit_size: Decimal | None) -> Decimal | None:
    if unit_size is None or unit_size <= ZERO:
        return None
    return quantize_market_value(value / unit_size)


def decimal_from_payload(payload: dict[str, object], key: str) -> Decimal:
    value = payload.get(key)
    if value is None:
        return ZERO
    return Decimal(str(value))


def sign(value: Decimal) -> int:
    return 1 if value > ZERO else -1


def quantize_market_value(value: Decimal) -> Decimal:
    return value.quantize(MARKET_VALUE_QUANT, rounding=ROUND_HALF_UP)
