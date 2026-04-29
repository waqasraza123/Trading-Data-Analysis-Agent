from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candles.models import Candle
from app.modules.candles.schemas import (
    CandleOriginType,
    CandleUpsertResult,
    CandleUpsertStatus,
    NormalizedCandleInput,
)


class CandleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_existing_candle(self, candle: NormalizedCandleInput) -> Candle | None:
        statement = select(Candle).where(
            Candle.workspace_id == candle.workspace_id,
            Candle.symbol_id == candle.symbol_id,
            Candle.source_id == candle.source_id,
            Candle.timeframe == candle.timeframe.value,
            Candle.timestamp == candle.timestamp,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_normalized_candle(self, candle: NormalizedCandleInput) -> CandleUpsertResult:
        existing_candle = await self.get_existing_candle(candle)
        if existing_candle is None:
            inserted_candle = self.build_candle(candle)
            self.session.add(inserted_candle)
            await self.session.flush()
            await self.session.refresh(inserted_candle)
            return CandleUpsertResult(
                candle_id=inserted_candle.id,
                status=CandleUpsertStatus.INSERTED,
                message="Candle inserted",
            )
        if existing_candle.is_final and not candle.is_final:
            return CandleUpsertResult(
                candle_id=existing_candle.id,
                status=CandleUpsertStatus.IGNORED_LATE_PARTIAL,
                message="Existing final candle ignored later partial update",
            )
        if existing_candle.is_final and candle.is_final:
            if self.has_conflicting_final_values(existing_candle, candle):
                return CandleUpsertResult(
                    candle_id=existing_candle.id,
                    status=CandleUpsertStatus.CONFLICTING_FINAL,
                    message="Existing final candle conflicts with incoming final candle",
                )
            return CandleUpsertResult(
                candle_id=existing_candle.id,
                status=CandleUpsertStatus.DUPLICATE_FINAL,
                message="Incoming final candle matches existing final candle",
            )
        self.apply_candle_values(existing_candle, candle)
        await self.session.flush()
        await self.session.refresh(existing_candle)
        return CandleUpsertResult(
            candle_id=existing_candle.id,
            status=(
                CandleUpsertStatus.FINALIZED
                if candle.is_final
                else CandleUpsertStatus.UPDATED_PARTIAL
            ),
            message="Candle finalized" if candle.is_final else "Partial candle updated",
        )

    async def fetch_window(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        source_id: UUID | None = None,
        include_partial: bool = False,
    ) -> list[Candle]:
        statement: Select[tuple[Candle]] = select(Candle).where(
            Candle.workspace_id == workspace_id,
            Candle.symbol_id == symbol_id,
            Candle.timeframe == timeframe,
            Candle.timestamp >= start_time,
            Candle.timestamp <= end_time,
        )
        if source_id is not None:
            statement = statement.where(Candle.source_id == source_id)
        if not include_partial:
            statement = statement.where(Candle.is_final.is_(True))
        result = await self.session.execute(statement.order_by(Candle.timestamp.asc()))
        return list(result.scalars().all())

    def build_candle(self, candle: NormalizedCandleInput) -> Candle:
        import_batch_id = (
            candle.origin_reference_id
            if candle.origin_type in {CandleOriginType.CSV_IMPORT, CandleOriginType.JSON_IMPORT}
            else None
        )
        live_feed_event_id = (
            candle.origin_reference_id if candle.origin_type == CandleOriginType.LIVE_FEED else None
        )
        return Candle(
            workspace_id=candle.workspace_id,
            symbol_id=candle.symbol_id,
            source_id=candle.source_id,
            import_batch_id=import_batch_id,
            live_feed_event_id=live_feed_event_id,
            timeframe=candle.timeframe.value,
            timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            is_final=candle.is_final,
        )

    def apply_candle_values(self, existing_candle: Candle, candle: NormalizedCandleInput) -> None:
        existing_candle.open = candle.open
        existing_candle.high = candle.high
        existing_candle.low = candle.low
        existing_candle.close = candle.close
        existing_candle.volume = candle.volume
        existing_candle.is_final = candle.is_final
        if candle.origin_type == CandleOriginType.LIVE_FEED:
            existing_candle.live_feed_event_id = candle.origin_reference_id

    def has_conflicting_final_values(
        self,
        existing_candle: Candle,
        candle: NormalizedCandleInput,
    ) -> bool:
        return (
            self.decimal_changed(existing_candle.open, candle.open)
            or self.decimal_changed(existing_candle.high, candle.high)
            or self.decimal_changed(existing_candle.low, candle.low)
            or self.decimal_changed(existing_candle.close, candle.close)
            or self.optional_decimal_changed(existing_candle.volume, candle.volume)
        )

    def decimal_changed(self, current_value: Decimal, incoming_value: Decimal) -> bool:
        return current_value != incoming_value

    def optional_decimal_changed(
        self,
        current_value: Decimal | None,
        incoming_value: Decimal | None,
    ) -> bool:
        return current_value != incoming_value
