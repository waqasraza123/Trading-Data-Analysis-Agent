import asyncio
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from app.core.errors import AppError
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.live.models import LiveFeedEventType
from app.modules.live.providers.base import LiveProvider, LiveProviderDisconnectedError
from app.modules.live.schemas import LiveProviderMessage, NormalizedLiveProviderEvent


class MockLiveProvider(LiveProvider):
    name = "mock"

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def subscribe(self, symbol: str, timeframe: str) -> None:
        return None

    async def unsubscribe(self, symbol: str, timeframe: str) -> None:
        return None

    async def stream_messages(
        self,
        symbol: str,
        timeframe: str,
        config_json: Mapping[str, object],
    ) -> AsyncIterator[LiveProviderMessage]:
        repeat = bool(config_json.get("mock_repeat", False))
        delay_seconds = float_from_config(config_json.get("mock_event_delay_seconds", 0))
        disconnect_after = config_json.get("mock_disconnect_after_events")
        emitted_count = 0
        while True:
            for item in self.runtime_message_items(
                symbol=symbol,
                timeframe=timeframe,
                config_json=config_json,
            ):
                if isinstance(disconnect_after, int) and emitted_count == disconnect_after:
                    raise LiveProviderDisconnectedError("Mock provider disconnected")
                message = self.build_configured_message(item) if isinstance(item, dict) else item
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)
                emitted_count += 1
                yield message
            if not repeat:
                return

    def runtime_message_items(
        self,
        symbol: str,
        timeframe: str,
        config_json: Mapping[str, object],
    ) -> list[LiveProviderMessage | dict[str, object]]:
        configured_events = config_json.get("mock_events")
        if isinstance(configured_events, list):
            configured_items: list[LiveProviderMessage | dict[str, object]] = []
            for item in configured_events:
                if not isinstance(item, dict):
                    raise AppError(422, "invalid_mock_event", "Mock runtime events must be objects")
                configured_items.append(item)
            return configured_items
        return list(
            self.default_runtime_messages(
                symbol=symbol,
                timeframe=timeframe,
                config_json=config_json,
            )
        )

    def build_configured_message(self, item: object) -> LiveProviderMessage:
        if not isinstance(item, dict):
            raise AppError(422, "invalid_mock_event", "Mock runtime events must be objects")
        if item.get("mockControl") == "disconnect" or item.get("mock_control") == "disconnect":
            raise LiveProviderDisconnectedError("Mock provider disconnected")
        return LiveProviderMessage.model_validate(item)

    def default_runtime_messages(
        self,
        symbol: str,
        timeframe: str,
        config_json: Mapping[str, object],
    ) -> list[LiveProviderMessage]:
        timestamp = datetime(2026, 4, 29, 10, 0, tzinfo=UTC)
        messages = [
            self.build_candle_message(LiveFeedEventType.CANDLE_PARTIAL, timestamp, "65025.00"),
            self.build_candle_message(LiveFeedEventType.CANDLE_FINAL, timestamp, "65040.00"),
            self.build_candle_message(LiveFeedEventType.CANDLE_FINAL, timestamp, "65040.00"),
            LiveProviderMessage(
                event_type=LiveFeedEventType.HEARTBEAT,
                provider_timestamp=timestamp + timedelta(seconds=70),
                payload_json={"symbol": symbol, "timeframe": timeframe},
            ),
            LiveProviderMessage(
                event_type=LiveFeedEventType.RECONNECT,
                provider_timestamp=timestamp + timedelta(seconds=80),
                payload_json={"symbol": symbol, "timeframe": timeframe},
            ),
            self.build_candle_message(
                LiveFeedEventType.CANDLE_PARTIAL,
                timestamp - timedelta(minutes=1),
                "64990.00",
            ),
        ]
        if bool(config_json.get("mock_include_malformed", False)):
            messages.append(
                LiveProviderMessage(
                    event_type=LiveFeedEventType.CANDLE_PARTIAL,
                    provider_timestamp=timestamp + timedelta(seconds=90),
                    payload_json={"candle": {"timestamp": timestamp.isoformat()}},
                )
            )
        return messages

    def build_candle_message(
        self,
        event_type: LiveFeedEventType,
        timestamp: datetime,
        close: str,
    ) -> LiveProviderMessage:
        return LiveProviderMessage(
            event_type=event_type,
            provider_timestamp=timestamp,
            payload_json={
                "candle": {
                    "timestamp": timestamp.isoformat(),
                    "open": "65000.00",
                    "high": "65050.00",
                    "low": "64980.00",
                    "close": close,
                    "volume": "18.20",
                }
            },
        )

    def normalize_message(self, payload: LiveProviderMessage) -> NormalizedLiveProviderEvent:
        if payload.event_type in {
            LiveFeedEventType.CANDLE_PARTIAL,
            LiveFeedEventType.CANDLE_FINAL,
        }:
            return self.normalize_candle_message(payload)
        if payload.event_type == LiveFeedEventType.ERROR:
            return NormalizedLiveProviderEvent(
                event_type=payload.event_type,
                provider_timestamp=payload.provider_timestamp,
                payload_json=payload.payload_json,
                error_message=str(payload.payload_json.get("errorMessage", "Provider error")),
            )
        return NormalizedLiveProviderEvent(
            event_type=payload.event_type,
            provider_timestamp=payload.provider_timestamp,
            payload_json=payload.payload_json,
        )

    def normalize_candle_message(
        self,
        payload: LiveProviderMessage,
    ) -> NormalizedLiveProviderEvent:
        candle_payload = payload.payload_json.get("candle", payload.payload_json)
        if not isinstance(candle_payload, dict):
            raise AppError(422, "invalid_live_payload", "Live candle payload must be an object")
        try:
            candle = RawCandlePayload.model_validate(candle_payload)
        except ValidationError as error:
            raise AppError(
                422,
                "invalid_live_candle_payload",
                str(error.errors()[0]["msg"]),
            ) from error
        return NormalizedLiveProviderEvent(
            event_type=payload.event_type,
            provider_timestamp=payload.provider_timestamp or candle.timestamp,
            payload_json=payload.payload_json,
            candle=candle,
        )


def float_from_config(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0
