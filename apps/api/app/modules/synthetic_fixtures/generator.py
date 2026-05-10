from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from random import Random

from app.core.errors import AppError
from app.modules.candles.timeframes import timeframe_duration
from app.modules.synthetic_fixtures.export import build_json_import_payload, candles_to_csv
from app.modules.synthetic_fixtures.patterns import CandleShape, shapes_for_pattern
from app.modules.synthetic_fixtures.schemas import (
    SyntheticFixtureCandle,
    SyntheticFixtureGenerateRequest,
    SyntheticFixtureGenerateResponse,
    SyntheticFixtureMetadata,
    SyntheticFixtureOutputFormat,
    SyntheticFixturePattern,
    SyntheticVolumeBehavior,
)

DEFAULT_REQUEST_START_PRICE = Decimal("1.1000")
DEFAULT_REQUEST_VOLATILITY = Decimal("0.0005")


@dataclass(frozen=True)
class EffectiveFixtureRequest:
    symbol: str
    start_price: Decimal
    volatility: Decimal


class SyntheticFixtureGenerator:
    def __init__(self, default_seed: int) -> None:
        self.default_seed = default_seed

    def generate(
        self,
        request: SyntheticFixtureGenerateRequest,
    ) -> SyntheticFixtureGenerateResponse:
        seed = request.seed if request.seed is not None else self.default_seed
        effective = effective_fixture_request(request)
        rng = Random(seed)
        quantum = price_quantum(effective.symbol, effective.start_price)
        shapes = shapes_for_pattern(
            pattern=request.pattern,
            candle_count=request.candle_count,
            volatility=effective.volatility,
        )
        skipped_indexes = missing_candle_indexes(request.pattern, request.candle_count)
        candles: list[SyntheticFixtureCandle] = []
        malformed_indices: list[int] = []
        missing_timestamps: list[datetime] = []
        current_price = effective.start_price
        duration = timeframe_duration(request.timeframe)
        for index, shape in enumerate(shapes):
            timestamp = request.start_time + duration * index
            candle = build_candle(
                timestamp=timestamp,
                current_price=current_price,
                shape=shape,
                quantum=quantum,
                volume=volume_for_index(
                    index=index,
                    behavior=request.volume_behavior,
                    shape=shape,
                    rng=rng,
                ),
                rng=rng,
            )
            current_price = candle.close
            if index in skipped_indexes:
                missing_timestamps.append(timestamp)
                continue
            candles.append(candle)
        if request.include_malformed and candles:
            malformed_index = len(candles) - 1
            candles[malformed_index] = malformed_candle(candles[malformed_index], quantum)
            malformed_indices.append(malformed_index)
        ohlc_valid = all(candle_has_valid_ohlc(candle) for candle in candles)
        csv_text = None
        json_import_payload = None
        if request.output_format in {
            SyntheticFixtureOutputFormat.CSV,
            SyntheticFixtureOutputFormat.FULL,
        }:
            csv_text = candles_to_csv(candles)
        if request.output_format == SyntheticFixtureOutputFormat.JSON_IMPORT_PAYLOAD or (
            request.output_format == SyntheticFixtureOutputFormat.FULL
            and request.workspace_id is not None
            and request.source_id is not None
            and request.symbol_id is not None
        ):
            json_import_payload = build_json_import_payload(
                workspace_id=request.workspace_id,
                user_id=request.user_id,
                source_id=request.source_id,
                symbol_id=request.symbol_id,
                timeframe=request.timeframe.value,
                candles=candles,
            )
        if request.output_format == SyntheticFixtureOutputFormat.JSON_IMPORT_PAYLOAD:
            csv_text = None
        metadata = SyntheticFixtureMetadata(
            pattern=request.pattern,
            symbol=effective.symbol,
            timeframe=request.timeframe,
            seed=seed,
            requested_candle_count=request.candle_count,
            generated_candle_count=len(candles),
            start_time=request.start_time,
            end_time=candles[-1].timestamp if candles else None,
            start_price=effective.start_price,
            volatility=effective.volatility,
            volume_behavior=request.volume_behavior,
            output_format=request.output_format,
            malformed_indices=malformed_indices,
            missing_timestamps=missing_timestamps,
            ohlc_valid=ohlc_valid,
        )
        return SyntheticFixtureGenerateResponse(
            symbol=effective.symbol,
            timeframe=request.timeframe,
            pattern=request.pattern,
            candles=candles,
            csv_text=csv_text,
            json_import_payload=json_import_payload,
            metadata=metadata,
        )


def effective_fixture_request(
    request: SyntheticFixtureGenerateRequest,
) -> EffectiveFixtureRequest:
    symbol = request.symbol
    start_price = request.start_price
    volatility = request.volatility
    if request.pattern == SyntheticFixturePattern.JPY_PAIR_PIP_SAMPLE:
        if request.symbol == "EURUSD":
            symbol = "USDJPY"
        if request.start_price == DEFAULT_REQUEST_START_PRICE:
            start_price = Decimal("145.500")
        if request.volatility == DEFAULT_REQUEST_VOLATILITY:
            volatility = Decimal("0.010")
    if request.pattern == SyntheticFixturePattern.CRYPTO_TICK_SAMPLE:
        if request.symbol == "EURUSD":
            symbol = "BTCUSDT"
        if request.start_price == DEFAULT_REQUEST_START_PRICE:
            start_price = Decimal("65000.00")
        if request.volatility == DEFAULT_REQUEST_VOLATILITY:
            volatility = Decimal("25.00")
    if volatility >= start_price:
        raise AppError(
            422,
            "volatility_exceeds_price",
            "volatility must be smaller than start_price",
        )
    return EffectiveFixtureRequest(
        symbol=symbol,
        start_price=start_price,
        volatility=volatility,
    )


def build_candle(
    *,
    timestamp: datetime,
    current_price: Decimal,
    shape: CandleShape,
    quantum: Decimal,
    volume: Decimal | None,
    rng: Random,
) -> SyntheticFixtureCandle:
    open_price = quantize_price(current_price, quantum)
    close_price = quantize_price(max(current_price + shape.move, quantum), quantum)
    upper_wick = quantize_price(shape.upper_wick * jitter(rng), quantum)
    lower_wick = quantize_price(shape.lower_wick * jitter(rng), quantum)
    high = quantize_price(max(open_price, close_price) + max(upper_wick, quantum), quantum)
    low = quantize_price(
        max(min(open_price, close_price) - max(lower_wick, quantum), quantum),
        quantum,
    )
    if high < max(open_price, close_price):
        high = max(open_price, close_price)
    if low > min(open_price, close_price):
        low = min(open_price, close_price)
    return SyntheticFixtureCandle(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        volume=volume,
    )


def volume_for_index(
    *,
    index: int,
    behavior: SyntheticVolumeBehavior,
    shape: CandleShape,
    rng: Random,
) -> Decimal | None:
    if behavior == SyntheticVolumeBehavior.NONE:
        return None
    base = Decimal("100")
    if behavior == SyntheticVolumeBehavior.TREND:
        base += Decimal(index * 4)
    if behavior == SyntheticVolumeBehavior.VOLATILE:
        base += Decimal(rng.randint(0, 60))
    return (base * shape.volume_multiplier).quantize(Decimal("0.01"))


def missing_candle_indexes(
    pattern: SyntheticFixturePattern,
    candle_count: int,
) -> set[int]:
    if pattern != SyntheticFixturePattern.MISSING_CANDLE_GAP:
        return set()
    first_gap = max(1, candle_count // 3)
    second_gap = max(first_gap + 2, (candle_count * 2) // 3)
    return {index for index in {first_gap, first_gap + 1, second_gap} if 0 <= index < candle_count}


def malformed_candle(
    candle: SyntheticFixtureCandle,
    quantum: Decimal,
) -> SyntheticFixtureCandle:
    invalid_high = max(min(candle.open, candle.close) - quantum, quantum)
    return SyntheticFixtureCandle(
        timestamp=candle.timestamp,
        open=candle.open,
        high=invalid_high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
    )


def candle_has_valid_ohlc(candle: SyntheticFixtureCandle) -> bool:
    return candle.high >= max(candle.open, candle.close) and candle.low <= min(
        candle.open,
        candle.close,
    )


def price_quantum(symbol: str, start_price: Decimal) -> Decimal:
    if "JPY" in symbol:
        return Decimal("0.001")
    if start_price >= Decimal("1000"):
        return Decimal("0.01")
    return Decimal("0.0001")


def quantize_price(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def jitter(rng: Random) -> Decimal:
    return Decimal("0.85") + Decimal(rng.randint(0, 30)) / Decimal("100")
