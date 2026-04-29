from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from pydantic import BaseModel

from app.core.errors import AppError
from app.modules.candles.schemas import CandleOriginType, NormalizedCandleInput
from app.modules.candles.timeframes import Timeframe, normalize_timestamp


class RawCandlePayload(BaseModel):
    timestamp: datetime
    open: str | int | float | Decimal
    high: str | int | float | Decimal
    low: str | int | float | Decimal
    close: str | int | float | Decimal
    volume: str | int | float | Decimal | None = None


def decimal_from_market_value(value: str | int | float | Decimal, field_name: str) -> Decimal:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise AppError(422, f"invalid_{field_name}", f"{field_name} must be numeric") from error
    if not decimal_value.is_finite():
        raise AppError(422, f"invalid_{field_name}", f"{field_name} must be finite")
    return decimal_value


def normalize_candle_payload(
    payload: RawCandlePayload,
    workspace_id: UUID,
    symbol_id: UUID,
    source_id: UUID,
    timeframe: Timeframe,
    is_final: bool,
    origin_type: CandleOriginType,
    origin_reference_id: UUID | None = None,
) -> NormalizedCandleInput:
    return NormalizedCandleInput(
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        source_id=source_id,
        timeframe=timeframe,
        timestamp=normalize_timestamp(payload.timestamp),
        open=decimal_from_market_value(payload.open, "open"),
        high=decimal_from_market_value(payload.high, "high"),
        low=decimal_from_market_value(payload.low, "low"),
        close=decimal_from_market_value(payload.close, "close"),
        volume=(
            decimal_from_market_value(payload.volume, "volume")
            if payload.volume is not None
            else None
        ),
        is_final=is_final,
        origin_type=origin_type,
        origin_reference_id=origin_reference_id,
    )
