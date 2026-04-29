from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.candles.quality import CandleQualityReport
from app.modules.candles.schemas import CandleCountRead, CandleRead
from app.modules.candles.service import CandleService
from app.modules.candles.timeframes import Timeframe

router = APIRouter(prefix="/candles", tags=["candles"])


def get_candle_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> CandleService:
    return CandleService(session)


@router.get("", response_model=list[CandleRead])
async def list_candles(
    service: Annotated[CandleService, Depends(get_candle_service)],
    workspace_id: UUID,
    symbol_id: UUID,
    timeframe: Timeframe,
    start_time: datetime,
    end_time: datetime,
    source_id: UUID | None = None,
    is_final: bool | None = True,
    limit: Annotated[int, Query(ge=1, le=500)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CandleRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    candles = await service.list_candles(
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        source_id=source_id,
        is_final=is_final,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [CandleRead.model_validate(candle) for candle in candles]


@router.get("/count", response_model=CandleCountRead)
async def count_candles(
    service: Annotated[CandleService, Depends(get_candle_service)],
    workspace_id: UUID,
    symbol_id: UUID,
    timeframe: Timeframe,
    start_time: datetime,
    end_time: datetime,
    source_id: UUID | None = None,
    is_final: bool | None = True,
) -> CandleCountRead:
    count = await service.count_candles(
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        source_id=source_id,
        is_final=is_final,
    )
    return CandleCountRead(count=count)


@router.get("/quality", response_model=CandleQualityReport)
async def get_candle_quality(
    service: Annotated[CandleService, Depends(get_candle_service)],
    workspace_id: UUID,
    symbol_id: UUID,
    timeframe: Timeframe,
    start_time: datetime,
    end_time: datetime,
    source_id: UUID | None = None,
) -> CandleQualityReport:
    return await service.calculate_window_quality(
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        source_id=source_id,
    )


@router.get("/latest", response_model=CandleRead)
async def get_latest_candle(
    service: Annotated[CandleService, Depends(get_candle_service)],
    workspace_id: UUID,
    symbol_id: UUID,
    timeframe: Timeframe,
    source_id: UUID | None = None,
    is_final: bool | None = True,
) -> CandleRead:
    candle = await service.get_latest_candle(
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        timeframe=timeframe,
        source_id=source_id,
        is_final=is_final,
    )
    return CandleRead.model_validate(candle)
