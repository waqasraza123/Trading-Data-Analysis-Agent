from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.candles.schemas import CandleOriginType
from app.modules.candles.timeframes import Timeframe
from app.modules.provider_polling.adapters.base import ProviderPollingFetchRequest
from app.modules.provider_polling.adapters.binance_public_rest import (
    build_klines_url,
    parse_kline_item,
)
from app.modules.provider_polling.adapters.generic_ohlc_http import GenericOhlcHttpPollingAdapter
from app.modules.provider_polling.adapters.mock import MockPollingProviderAdapter
from app.modules.provider_polling.normalizer import normalize_provider_candle
from app.modules.provider_polling.schemas import ProviderCandle


@pytest.mark.asyncio
async def test_mock_polling_provider_generates_final_candles() -> None:
    adapter = MockPollingProviderAdapter()
    result = await adapter.fetch_candles(
        ProviderPollingFetchRequest(
            provider="mock_polling",
            provider_symbol="BTCUSDT",
            timeframe=Timeframe.ONE_MINUTE,
            start_time=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
            end_time=None,
            limit=2,
            timeout_seconds=20,
            user_agent="test-agent",
            binance_public_rest_base_url="https://api.binance.com",
            request_metadata_json={},
        )
    )

    assert [candle.timestamp.minute for candle in result.candles] == [0, 1]
    assert all(candle.is_final for candle in result.candles)
    assert result.provider_metadata["provider"] == "mock_polling"


def test_binance_public_rest_url_uses_public_klines_endpoint() -> None:
    url = build_klines_url(
        ProviderPollingFetchRequest(
            provider="binance_public_rest",
            provider_symbol="btcusdt",
            timeframe=Timeframe.FIVE_MINUTES,
            start_time=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
            end_time=datetime(2026, 4, 29, 11, 0, tzinfo=UTC),
            limit=500,
            timeout_seconds=20,
            user_agent="test-agent",
            binance_public_rest_base_url="https://api.binance.com",
            request_metadata_json={},
        )
    )

    assert url.startswith("https://api.binance.com/api/v3/klines?")
    assert "symbol=BTCUSDT" in url
    assert "interval=5m" in url
    assert "limit=500" in url


def test_binance_kline_parser_normalizes_public_rest_candle() -> None:
    candle = parse_kline_item(
        [
            1777456800000,
            "65000.00",
            "65050.00",
            "64980.00",
            "65025.00",
            "12.50",
            1777456859999,
        ],
        ProviderPollingFetchRequest(
            provider="binance_public_rest",
            provider_symbol="BTCUSDT",
            timeframe=Timeframe.ONE_MINUTE,
            start_time=None,
            end_time=None,
            limit=1,
            timeout_seconds=20,
            user_agent="test-agent",
            binance_public_rest_base_url="https://api.binance.com",
            request_metadata_json={},
        ),
        now_ms=1777456860000,
    )

    assert candle.provider_symbol == "BTCUSDT"
    assert candle.open == Decimal("65000.00")
    assert candle.volume == Decimal("12.50")
    assert candle.is_final is True


@pytest.mark.asyncio
async def test_generic_ohlc_http_adapter_is_safe_stub() -> None:
    result = await GenericOhlcHttpPollingAdapter().fetch_candles(
        ProviderPollingFetchRequest(
            provider="generic_ohlc_http",
            provider_symbol="BTCUSDT",
            timeframe=Timeframe.ONE_MINUTE,
            start_time=None,
            end_time=None,
            limit=1,
            timeout_seconds=20,
            user_agent="test-agent",
            binance_public_rest_base_url="https://api.binance.com",
            request_metadata_json={},
        )
    )

    assert result.candles == []
    assert result.errors[0].code == "generic_adapter_not_configured"


def test_provider_polling_normalizer_uses_api_polling_origin() -> None:
    workspace_id = uuid4()
    source_id = uuid4()
    symbol_id = uuid4()
    request_id = uuid4()

    normalized = normalize_provider_candle(
        provider_candle=ProviderCandle(
            provider_symbol="BTCUSDT",
            timeframe=Timeframe.ONE_MINUTE,
            timestamp=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
            open=Decimal("65000.00"),
            high=Decimal("65050.00"),
            low=Decimal("64980.00"),
            close=Decimal("65025.00"),
            volume=Decimal("12.50"),
            is_final=True,
        ),
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        source_id=source_id,
        polling_request_id=request_id,
    )

    assert normalized.origin_type == CandleOriginType.API_POLLING
    assert normalized.origin_reference_id == request_id
    assert normalized.workspace_id == workspace_id
    assert normalized.source_id == source_id
