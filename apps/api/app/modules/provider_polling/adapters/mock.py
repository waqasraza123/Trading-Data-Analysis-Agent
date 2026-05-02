from datetime import UTC, datetime
from decimal import Decimal

from app.modules.candles.timeframes import timeframe_duration
from app.modules.provider_polling.adapters.base import (
    ProviderPollingAdapter,
    ProviderPollingFetchRequest,
    ProviderPollingResult,
)
from app.modules.provider_polling.schemas import ProviderCandle


class MockPollingProviderAdapter(ProviderPollingAdapter):
    provider_key = "mock_polling"

    async def fetch_candles(
        self,
        request: ProviderPollingFetchRequest,
    ) -> ProviderPollingResult:
        candles: list[ProviderCandle] = []
        current_timestamp = request.start_time or default_start_time()
        duration = timeframe_duration(request.timeframe)
        for index in range(request.limit):
            if request.end_time is not None and current_timestamp > request.end_time:
                break
            open_price = Decimal("65000.00") + Decimal(index)
            close_price = open_price + Decimal("5.00")
            candles.append(
                ProviderCandle(
                    provider_symbol=request.provider_symbol,
                    timeframe=request.timeframe,
                    timestamp=current_timestamp,
                    open=open_price,
                    high=close_price + Decimal("10.00"),
                    low=open_price - Decimal("10.00"),
                    close=close_price,
                    volume=Decimal("10.00") + Decimal(index),
                    is_final=True,
                    raw_item_json={
                        "provider": self.provider_key,
                        "sequence": index + 1,
                        "providerSymbol": request.provider_symbol,
                    },
                )
            )
            current_timestamp += duration
        return ProviderPollingResult(
            candles=candles,
            provider_metadata={
                "provider": self.provider_key,
                "requested_url": None,
                "generated": True,
            },
            warnings=[],
            errors=[],
        )


def default_start_time() -> datetime:
    return datetime(2026, 4, 29, 10, 0, tzinfo=UTC)
