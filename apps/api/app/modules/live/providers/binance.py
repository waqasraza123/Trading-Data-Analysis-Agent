from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.core.errors import AppError
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.live.models import LiveFeedEventType
from app.modules.live.providers.base import LiveProvider
from app.modules.live.schemas import LiveProviderMessage, NormalizedLiveProviderEvent


class BinanceLiveProvider(LiveProvider):
    name = "binance"

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def subscribe(self, symbol: str, timeframe: str) -> None:
        return None

    async def unsubscribe(self, symbol: str, timeframe: str) -> None:
        return None

    def normalize_message(self, payload: LiveProviderMessage) -> NormalizedLiveProviderEvent:
        kline_payload = payload.payload_json.get("k")
        if not isinstance(kline_payload, dict):
            raise AppError(
                422,
                "invalid_binance_payload",
                "Binance payload must include kline data",
            )
        try:
            candle = RawCandlePayload(
                timestamp=datetime_from_milliseconds(kline_payload["t"]),
                open=Decimal(str(kline_payload["o"])),
                high=Decimal(str(kline_payload["h"])),
                low=Decimal(str(kline_payload["l"])),
                close=Decimal(str(kline_payload["c"])),
                volume=Decimal(str(kline_payload["v"])),
            )
            is_final = bool(kline_payload.get("x", False))
        except (KeyError, TypeError, ValueError) as error:
            raise AppError(
                422,
                "invalid_binance_kline",
                "Binance kline payload is missing required candle fields",
            ) from error
        return NormalizedLiveProviderEvent(
            event_type=(
                LiveFeedEventType.CANDLE_FINAL
                if is_final
                else LiveFeedEventType.CANDLE_PARTIAL
            ),
            provider_timestamp=(
                payload.provider_timestamp or datetime_from_event(payload.payload_json)
            ),
            payload_json=payload.payload_json,
            candle=candle,
        )


def datetime_from_event(payload: dict[str, Any]) -> datetime | None:
    event_time = payload.get("E")
    if event_time is None:
        return None
    return datetime_from_milliseconds(event_time)


def datetime_from_milliseconds(value: object) -> datetime:
    if not isinstance(value, int | float | str):
        msg = "timestamp value must be numeric"
        raise ValueError(msg)
    return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
