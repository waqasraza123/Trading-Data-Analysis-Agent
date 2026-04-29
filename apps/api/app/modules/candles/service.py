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
from app.modules.candles.timeframes import Timeframe, normalize_timestamp
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
        normalized_start_time = normalize_timestamp(start_time)
        normalized_end_time = normalize_timestamp(end_time)
        await self.validate_query_boundary(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            start_time=normalized_start_time,
            end_time=normalized_end_time,
        )
        return await self.candle_repository.fetch_window(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe.value,
            start_time=normalized_start_time,
            end_time=normalized_end_time,
            source_id=source_id,
            include_partial=include_partial,
        )

    async def list_candles(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        source_id: UUID | None,
        is_final: bool | None,
        limit: int | None,
        offset: int,
    ) -> list[Candle]:
        normalized_start_time = normalize_timestamp(start_time)
        normalized_end_time = normalize_timestamp(end_time)
        await self.validate_query_boundary(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            start_time=normalized_start_time,
            end_time=normalized_end_time,
        )
        return await self.candle_repository.list_candles(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe.value,
            start_time=normalized_start_time,
            end_time=normalized_end_time,
            source_id=source_id,
            is_final=is_final,
            limit=limit,
            offset=offset,
        )

    async def count_candles(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        source_id: UUID | None,
        is_final: bool | None,
    ) -> int:
        normalized_start_time = normalize_timestamp(start_time)
        normalized_end_time = normalize_timestamp(end_time)
        await self.validate_query_boundary(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            start_time=normalized_start_time,
            end_time=normalized_end_time,
        )
        return await self.candle_repository.count_candles(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe.value,
            start_time=normalized_start_time,
            end_time=normalized_end_time,
            source_id=source_id,
            is_final=is_final,
        )

    async def get_latest_candle(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        source_id: UUID | None,
        is_final: bool | None,
    ) -> Candle:
        await self.validate_query_boundary(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            start_time=None,
            end_time=None,
        )
        candle = await self.candle_repository.get_latest_candle(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe.value,
            source_id=source_id,
            is_final=is_final,
        )
        if candle is None:
            raise AppError(404, "latest_candle_not_found", "Latest candle not found")
        return candle

    async def calculate_window_quality(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        source_id: UUID | None,
    ) -> CandleQualityReport:
        normalized_start_time = normalize_timestamp(start_time)
        normalized_end_time = normalize_timestamp(end_time)
        candles = await self.list_candles(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            start_time=normalized_start_time,
            end_time=normalized_end_time,
            source_id=source_id,
            is_final=None,
            limit=None,
            offset=0,
        )
        return self.calculate_quality_report(
            candles=candles,
            timeframe=timeframe,
            start_time=normalized_start_time,
            end_time=normalized_end_time,
        )

    async def fetch_warmup_window(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        warmup_start_time: datetime,
        analysis_start_time: datetime,
        source_id: UUID | None = None,
        include_partial: bool = False,
    ) -> list[Candle]:
        return await self.fetch_candle_window(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            start_time=warmup_start_time,
            end_time=analysis_start_time,
            source_id=source_id,
            include_partial=include_partial,
        )

    async def fetch_baseline_window(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        baseline_start_time: datetime,
        analysis_start_time: datetime,
        source_id: UUID | None = None,
    ) -> list[Candle]:
        return await self.fetch_candle_window(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            start_time=baseline_start_time,
            end_time=analysis_start_time,
            source_id=source_id,
            include_partial=False,
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

    async def validate_query_boundary(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> None:
        if start_time is not None and end_time is not None and start_time > end_time:
            raise AppError(422, "invalid_candle_window", "start_time must be before end_time")
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if source_id is None:
            return
        data_source = await self.data_source_repository.get_by_id(source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if data_source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )
