from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.signals.models import SignalBias, SignalClassificationStatus
from app.modules.symbols.models import MarketType

OUTCOME_MIN_FUTURE_CANDLES = 3
OUTCOME_EVALUATION_VERSION = "v1"
MIN_DIRECTIONAL_MOVE_RATIO = Decimal("0.0005")
SIDEWAYS_RANGE_RATIO = Decimal("0.0003")
REVERSAL_DOMINANCE_RATIO = Decimal("1.5000")
CONTINUATION_DOMINANCE_RATIO = Decimal("1.2500")


@dataclass(frozen=True)
class OutcomeCandle:
    timestamp: datetime
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True)
class OutcomeSymbolMetadata:
    market_type: str
    pip_size: Decimal | None = None
    tick_size: Decimal | None = None


@dataclass(frozen=True)
class OutcomeCalculationInput:
    bias: str
    classification_status: str
    reference_price: Decimal
    future_candles: list[OutcomeCandle]
    symbol_metadata: OutcomeSymbolMetadata
    min_future_candles: int = OUTCOME_MIN_FUTURE_CANDLES


@dataclass(frozen=True)
class OutcomeCalculationResult:
    evaluation_status: OutcomeEvaluationStatus
    outcome_label: OutcomeLabel
    future_candle_count: int
    max_favorable_move: Decimal
    max_adverse_move: Decimal
    net_move: Decimal
    max_favorable_pips: Decimal | None
    max_adverse_pips: Decimal | None
    net_pips: Decimal | None
    max_favorable_ticks: Decimal | None
    max_adverse_ticks: Decimal | None
    net_ticks: Decimal | None
    direction_followed: bool | None
    reversal_detected: bool
    movement_quality: str | None
    metadata_json: dict[str, object] = field(default_factory=dict)


class OutcomeCalculator:
    def calculate(self, payload: OutcomeCalculationInput) -> OutcomeCalculationResult:
        if len(payload.future_candles) < payload.min_future_candles:
            return insufficient_data_result(
                future_candle_count=len(payload.future_candles),
                minimum_required_candles=payload.min_future_candles,
            )
        if not is_directional_signal(payload.bias, payload.classification_status):
            return self.calculate_not_directional(payload)
        if payload.bias == SignalBias.BULLISH:
            return self.calculate_bullish(payload)
        if payload.bias == SignalBias.BEARISH:
            return self.calculate_bearish(payload)
        return self.calculate_not_directional(payload)

    def calculate_bullish(self, payload: OutcomeCalculationInput) -> OutcomeCalculationResult:
        highest_high = max(candle.high for candle in payload.future_candles)
        lowest_low = min(candle.low for candle in payload.future_candles)
        final_close = payload.future_candles[-1].close
        favorable = non_negative(highest_high - payload.reference_price)
        adverse = non_negative(payload.reference_price - lowest_low)
        net = final_close - payload.reference_price
        direction_followed = net > 0 or favorable >= directional_threshold(payload.reference_price)
        reversal_detected = adverse_dominates(favorable, adverse) or net <= -directional_threshold(
            payload.reference_price
        )
        label = directional_label(
            favorable=favorable,
            adverse=adverse,
            net=net,
            direction_followed=direction_followed,
            reversal_detected=reversal_detected,
            reference_price=payload.reference_price,
        )
        return build_result(
            payload=payload,
            status=OutcomeEvaluationStatus.EVALUATED,
            label=label,
            favorable=favorable,
            adverse=adverse,
            net=net,
            direction_followed=direction_followed,
            reversal_detected=reversal_detected,
        )

    def calculate_bearish(self, payload: OutcomeCalculationInput) -> OutcomeCalculationResult:
        highest_high = max(candle.high for candle in payload.future_candles)
        lowest_low = min(candle.low for candle in payload.future_candles)
        final_close = payload.future_candles[-1].close
        favorable = non_negative(payload.reference_price - lowest_low)
        adverse = non_negative(highest_high - payload.reference_price)
        net = payload.reference_price - final_close
        direction_followed = net > 0 or favorable >= directional_threshold(payload.reference_price)
        reversal_detected = adverse_dominates(favorable, adverse) or net <= -directional_threshold(
            payload.reference_price
        )
        label = directional_label(
            favorable=favorable,
            adverse=adverse,
            net=net,
            direction_followed=direction_followed,
            reversal_detected=reversal_detected,
            reference_price=payload.reference_price,
        )
        return build_result(
            payload=payload,
            status=OutcomeEvaluationStatus.EVALUATED,
            label=label,
            favorable=favorable,
            adverse=adverse,
            net=net,
            direction_followed=direction_followed,
            reversal_detected=reversal_detected,
        )

    def calculate_not_directional(self, payload: OutcomeCalculationInput) -> OutcomeCalculationResult:
        highest_high = max(candle.high for candle in payload.future_candles)
        lowest_low = min(candle.low for candle in payload.future_candles)
        final_close = payload.future_candles[-1].close
        absolute_range = non_negative(highest_high - lowest_low)
        net = final_close - payload.reference_price
        label = (
            OutcomeLabel.SIDEWAYS_AFTER_SIGNAL
            if absolute_range <= sideways_threshold(payload.reference_price)
            else OutcomeLabel.NOT_DIRECTIONAL
        )
        return build_result(
            payload=payload,
            status=OutcomeEvaluationStatus.SKIPPED_NOT_DIRECTIONAL,
            label=label,
            favorable=absolute_range,
            adverse=Decimal("0"),
            net=net,
            direction_followed=None,
            reversal_detected=False,
            extra_metadata={"notDirectionalReason": "bias_or_classification_status_not_directional"},
        )


def build_result(
    payload: OutcomeCalculationInput,
    status: OutcomeEvaluationStatus,
    label: OutcomeLabel,
    favorable: Decimal,
    adverse: Decimal,
    net: Decimal,
    direction_followed: bool | None,
    reversal_detected: bool,
    extra_metadata: dict[str, object] | None = None,
) -> OutcomeCalculationResult:
    pips = convert_to_pips(payload.symbol_metadata, favorable, adverse, net)
    ticks = convert_to_ticks(payload.symbol_metadata, favorable, adverse, net)
    metadata: dict[str, object] = {
        "thresholds": {
            "minimumDirectionalMoveRatio": str(MIN_DIRECTIONAL_MOVE_RATIO),
            "sidewaysRangeRatio": str(SIDEWAYS_RANGE_RATIO),
            "reversalDominanceRatio": str(REVERSAL_DOMINANCE_RATIO),
            "continuationDominanceRatio": str(CONTINUATION_DOMINANCE_RATIO),
        }
    }
    warnings = [*pips.warnings, *ticks.warnings]
    if warnings:
        metadata["warnings"] = warnings
    if extra_metadata:
        metadata.update(extra_metadata)
    return OutcomeCalculationResult(
        evaluation_status=status,
        outcome_label=label,
        future_candle_count=len(payload.future_candles),
        max_favorable_move=favorable,
        max_adverse_move=adverse,
        net_move=net,
        max_favorable_pips=pips.max_favorable,
        max_adverse_pips=pips.max_adverse,
        net_pips=pips.net,
        max_favorable_ticks=ticks.max_favorable,
        max_adverse_ticks=ticks.max_adverse,
        net_ticks=ticks.net,
        direction_followed=direction_followed,
        reversal_detected=reversal_detected,
        movement_quality=movement_quality(favorable, adverse, net, payload.reference_price),
        metadata_json=metadata,
    )


@dataclass(frozen=True)
class ConvertedMovement:
    max_favorable: Decimal | None
    max_adverse: Decimal | None
    net: Decimal | None
    warnings: list[str]


def convert_to_pips(
    symbol: OutcomeSymbolMetadata,
    favorable: Decimal,
    adverse: Decimal,
    net: Decimal,
) -> ConvertedMovement:
    if symbol.market_type != MarketType.FOREX:
        return ConvertedMovement(None, None, None, [])
    if symbol.pip_size is None:
        return ConvertedMovement(None, None, None, ["missing_pip_size"])
    return ConvertedMovement(
        max_favorable=favorable / symbol.pip_size,
        max_adverse=adverse / symbol.pip_size,
        net=net / symbol.pip_size,
        warnings=[],
    )


def convert_to_ticks(
    symbol: OutcomeSymbolMetadata,
    favorable: Decimal,
    adverse: Decimal,
    net: Decimal,
) -> ConvertedMovement:
    if symbol.market_type != MarketType.CRYPTO:
        return ConvertedMovement(None, None, None, [])
    if symbol.tick_size is None:
        return ConvertedMovement(None, None, None, ["missing_tick_size"])
    return ConvertedMovement(
        max_favorable=favorable / symbol.tick_size,
        max_adverse=adverse / symbol.tick_size,
        net=net / symbol.tick_size,
        warnings=[],
    )


def insufficient_data_result(
    future_candle_count: int,
    minimum_required_candles: int,
) -> OutcomeCalculationResult:
    return OutcomeCalculationResult(
        evaluation_status=OutcomeEvaluationStatus.INSUFFICIENT_FUTURE_DATA,
        outcome_label=OutcomeLabel.INSUFFICIENT_DATA,
        future_candle_count=future_candle_count,
        max_favorable_move=Decimal("0"),
        max_adverse_move=Decimal("0"),
        net_move=Decimal("0"),
        max_favorable_pips=None,
        max_adverse_pips=None,
        net_pips=None,
        max_favorable_ticks=None,
        max_adverse_ticks=None,
        net_ticks=None,
        direction_followed=None,
        reversal_detected=False,
        movement_quality=None,
        metadata_json={
            "minimumRequiredFutureCandles": minimum_required_candles,
            "observedFutureCandles": future_candle_count,
        },
    )


def is_directional_signal(bias: str, classification_status: str) -> bool:
    return classification_status == SignalClassificationStatus.SIGNAL and bias in {
        SignalBias.BULLISH,
        SignalBias.BEARISH,
    }


def directional_label(
    favorable: Decimal,
    adverse: Decimal,
    net: Decimal,
    direction_followed: bool,
    reversal_detected: bool,
    reference_price: Decimal,
) -> OutcomeLabel:
    threshold = directional_threshold(reference_price)
    if reversal_detected:
        return OutcomeLabel.REVERSAL
    if net > threshold and favorable >= adverse * CONTINUATION_DOMINANCE_RATIO:
        return OutcomeLabel.CONTINUATION
    if direction_followed and favorable > threshold:
        return OutcomeLabel.PARTIAL_FOLLOW_THROUGH
    if favorable <= threshold and adverse <= threshold:
        return OutcomeLabel.NO_FOLLOW_THROUGH
    return OutcomeLabel.NO_FOLLOW_THROUGH


def movement_quality(
    favorable: Decimal,
    adverse: Decimal,
    net: Decimal,
    reference_price: Decimal,
) -> str | None:
    threshold = directional_threshold(reference_price)
    if favorable <= threshold and adverse <= threshold:
        return "sideways"
    if adverse_dominates(favorable, adverse) or net < -threshold:
        return "reversal"
    if favorable >= adverse * CONTINUATION_DOMINANCE_RATIO and net > 0:
        return "efficient_follow_through"
    if favorable > threshold:
        return "mixed_follow_through"
    return "mixed"


def adverse_dominates(favorable: Decimal, adverse: Decimal) -> bool:
    if adverse <= 0:
        return False
    if favorable <= 0:
        return adverse > 0
    return adverse >= favorable * REVERSAL_DOMINANCE_RATIO


def directional_threshold(reference_price: Decimal) -> Decimal:
    return abs(reference_price) * MIN_DIRECTIONAL_MOVE_RATIO


def sideways_threshold(reference_price: Decimal) -> Decimal:
    return abs(reference_price) * SIDEWAYS_RANGE_RATIO


def non_negative(value: Decimal) -> Decimal:
    return max(value, Decimal("0"))
