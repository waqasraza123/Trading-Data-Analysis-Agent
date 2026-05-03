from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.modules.candles.models import Candle
from app.modules.candles.timeframes import Timeframe
from app.modules.timeframe_aggregation.aggregator import TimeframeAggregator


def make_candle(timestamp: datetime, open_value: str, close_value: str) -> Candle:
    high = max(Decimal(open_value), Decimal(close_value)) + Decimal("1")
    low = min(Decimal(open_value), Decimal(close_value)) - Decimal("1")
    return Candle(
        id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        source_id=uuid4(),
        timeframe="1m",
        timestamp=timestamp,
        open=Decimal(open_value),
        high=high,
        low=low,
        close=Decimal(close_value),
        volume=Decimal("10"),
        is_final=True,
    )


def test_aggregator_builds_complete_5m_candle_from_1m_final_candles() -> None:
    aggregator = TimeframeAggregator()
    start = datetime(2026, 5, 2, 12, 0, tzinfo=UTC)
    end = datetime(2026, 5, 2, 12, 4, tzinfo=UTC)
    window = aggregator.build_windows(Timeframe.ONE_MINUTE, Timeframe.FIVE_MINUTES, start, end)[0]
    candles = [
        make_candle(datetime(2026, 5, 2, 12, minute, tzinfo=UTC), str(100 + minute), str(101 + minute))
        for minute in range(5)
    ]

    candidate = aggregator.aggregate_window(window, candles)

    assert candidate is not None
    assert candidate.open == Decimal("100")
    assert candidate.close == Decimal("105")
    assert candidate.volume == Decimal("50")
    assert candidate.completeness_score == Decimal("1.00000")


def test_aggregator_skips_incomplete_window() -> None:
    aggregator = TimeframeAggregator()
    start = datetime(2026, 5, 2, 12, 0, tzinfo=UTC)
    end = datetime(2026, 5, 2, 12, 4, tzinfo=UTC)
    window = aggregator.build_windows(Timeframe.ONE_MINUTE, Timeframe.FIVE_MINUTES, start, end)[0]
    candles = [
        make_candle(datetime(2026, 5, 2, 12, minute, tzinfo=UTC), str(100 + minute), str(101 + minute))
        for minute in range(4)
    ]

    candidate = aggregator.aggregate_window(window, candles)

    assert candidate is None
