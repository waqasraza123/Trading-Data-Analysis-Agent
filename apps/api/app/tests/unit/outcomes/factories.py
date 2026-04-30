from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.modules.outcomes.calculator import (
    OutcomeCalculationInput,
    OutcomeCandle,
    OutcomeSymbolMetadata,
)
from app.modules.signals.models import SignalBias, SignalClassificationStatus
from app.modules.symbols.models import MarketType

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def candle(minutes: int, high: str, low: str, close: str) -> OutcomeCandle:
    return OutcomeCandle(
        timestamp=BASE_TIME + timedelta(minutes=minutes),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def calculation_input(
    bias: str = SignalBias.BULLISH,
    classification_status: str = SignalClassificationStatus.SIGNAL,
    reference_price: str = "100",
    candles: list[OutcomeCandle] | None = None,
    market_type: str = MarketType.FOREX,
    pip_size: str | None = "0.0001",
    tick_size: str | None = None,
) -> OutcomeCalculationInput:
    return OutcomeCalculationInput(
        bias=bias,
        classification_status=classification_status,
        reference_price=Decimal(reference_price),
        future_candles=candles
        or [
            candle(1, "101", "99.8", "100.5"),
            candle(2, "102", "100.4", "101.4"),
            candle(3, "103", "101.2", "102.2"),
        ],
        symbol_metadata=OutcomeSymbolMetadata(
            market_type=market_type,
            pip_size=Decimal(pip_size) if pip_size is not None else None,
            tick_size=Decimal(tick_size) if tick_size is not None else None,
        ),
    )


def service_signal() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        analysis_run_id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="1m",
        strategy_profile_key="default",
        strategy_profile_version="v1",
        pattern_type="breakout",
        bias=SignalBias.BULLISH,
        classification_status=SignalClassificationStatus.SIGNAL,
    )


def service_run(signal: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        id=signal.analysis_run_id,
        workspace_id=signal.workspace_id,
        symbol_id=signal.symbol_id,
        source_id=None,
        timeframe=signal.timeframe,
        start_time=BASE_TIME,
        end_time=BASE_TIME + timedelta(minutes=3),
        analysis_mode="historical",
        replayed_from_analysis_run_id=None,
    )
