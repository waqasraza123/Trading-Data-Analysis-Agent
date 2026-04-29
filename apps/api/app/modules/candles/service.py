from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.candles.models import Candle
from app.modules.candles.quality import (
    CandleQualityInput,
    CandleQualityReport,
    calculate_candle_quality,
)
from app.modules.candles.repository import CandleRepository
from app.modules.candles.schemas import CandleUpsertResult, NormalizedCandleInput
from app.modules.candles.timeframes import Timeframe
from app.modules.candles.validator import validate_candle
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.symbols.repository import SymbolRepository


class CandleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.candle_repository = CandleRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def validate_and_store_candle(
        self,
        candle: NormalizedCandleInput,
    ) -> CandleUpsertResult:
        symbol = await self.symbol_repository.get_by_id(candle.symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        data_source = await self.data_source_repository.get_by_id(candle.source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        validation_result = validate_candle(candle=candle, symbol=symbol, data_source=data_source)
        if not validation_result.is_valid:
            raise AppError(422, "invalid_candle", "Candle validation failed")
        result = await self.candle_repository.upsert_normalized_candle(candle)
        await self.session.commit()
        return result

    async def fetch_candle_window(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        source_id: UUID | None = None,
        include_partial: bool = False,
    ) -> list[Candle]:
        return await self.candle_repository.fetch_window(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe.value,
            start_time=start_time,
            end_time=end_time,
            source_id=source_id,
            include_partial=include_partial,
        )

    def calculate_quality_report(
        self,
        candles: list[Candle],
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
    ) -> CandleQualityReport:
        return calculate_candle_quality(
            candles=[
                CandleQualityInput(timestamp=candle.timestamp, is_final=candle.is_final)
                for candle in candles
            ],
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
        )
