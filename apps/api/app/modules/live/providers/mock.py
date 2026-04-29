from pydantic import ValidationError

from app.core.errors import AppError
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.live.models import LiveFeedEventType
from app.modules.live.providers.base import LiveProvider
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
