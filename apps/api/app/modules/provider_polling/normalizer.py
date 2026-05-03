from uuid import UUID

from app.modules.candles.normalizer import RawCandlePayload, normalize_candle_payload
from app.modules.candles.schemas import CandleOriginType, NormalizedCandleInput
from app.modules.provider_polling.schemas import ProviderCandle


def normalize_provider_candle(
    provider_candle: ProviderCandle,
    workspace_id: UUID,
    symbol_id: UUID,
    source_id: UUID,
    polling_request_id: UUID,
) -> NormalizedCandleInput:
    return normalize_candle_payload(
        payload=RawCandlePayload(
            timestamp=provider_candle.timestamp,
            open=provider_candle.open,
            high=provider_candle.high,
            low=provider_candle.low,
            close=provider_candle.close,
            volume=provider_candle.volume,
        ),
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        source_id=source_id,
        timeframe=provider_candle.timeframe,
        is_final=provider_candle.is_final,
        origin_type=CandleOriginType.API_POLLING,
        origin_reference_id=polling_request_id,
    )
