from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.candles.timeframes import Timeframe
from app.modules.timeframe_aggregation.models import CandleAggregationRunStatus
from app.modules.timeframe_aggregation.schemas import (
    CandleAggregationRunRead,
    DerivedCandleLineageRead,
    MultiTimeframeContextCreate,
    MultiTimeframeContextRead,
    TimeframeAggregationRunCreate,
)
from app.modules.timeframe_aggregation.service import (
    TimeframeAggregationService,
    context_payload_or_default,
)

router = APIRouter(tags=["timeframe-aggregation"])


def get_timeframe_aggregation_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> TimeframeAggregationService:
    return TimeframeAggregationService(session)


@router.post(
    "/timeframe-aggregation/runs",
    response_model=CandleAggregationRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_aggregation_run(
    payload: TimeframeAggregationRunCreate,
    service: Annotated[TimeframeAggregationService, Depends(get_timeframe_aggregation_service)],
) -> CandleAggregationRunRead:
    run = await service.aggregate_timeframe(payload)
    return CandleAggregationRunRead.model_validate(run)


@router.get("/timeframe-aggregation/runs/{run_id}", response_model=CandleAggregationRunRead)
async def get_aggregation_run(
    run_id: UUID,
    service: Annotated[TimeframeAggregationService, Depends(get_timeframe_aggregation_service)],
) -> CandleAggregationRunRead:
    run = await service.get_aggregation_run(run_id)
    return CandleAggregationRunRead.model_validate(run)


@router.get("/timeframe-aggregation/runs", response_model=list[CandleAggregationRunRead])
async def list_aggregation_runs(
    service: Annotated[TimeframeAggregationService, Depends(get_timeframe_aggregation_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
    symbol_id: UUID | None = None,
    status_filter: Annotated[CandleAggregationRunStatus | None, Query(alias="status")] = None,
    base_timeframe: Timeframe | None = None,
    target_timeframe: Timeframe | None = None,
) -> list[CandleAggregationRunRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    runs = await service.list_aggregation_runs(
        limit=pagination.limit,
        offset=pagination.offset,
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        status=status_filter.value if status_filter is not None else None,
        base_timeframe=base_timeframe.value if base_timeframe is not None else None,
        target_timeframe=target_timeframe.value if target_timeframe is not None else None,
    )
    return [CandleAggregationRunRead.model_validate(run) for run in runs]


@router.get(
    "/timeframe-aggregation/derived-candles/{candle_id}/lineage",
    response_model=list[DerivedCandleLineageRead],
)
async def get_derived_candle_lineage(
    candle_id: UUID,
    service: Annotated[TimeframeAggregationService, Depends(get_timeframe_aggregation_service)],
) -> list[DerivedCandleLineageRead]:
    lineage = await service.get_derived_lineage(candle_id)
    return [DerivedCandleLineageRead.model_validate(row) for row in lineage]


@router.post(
    "/analysis-runs/{analysis_run_id}/multi-timeframe-context",
    response_model=MultiTimeframeContextRead,
    status_code=status.HTTP_201_CREATED,
)
async def build_analysis_multi_timeframe_context(
    analysis_run_id: UUID,
    service: Annotated[TimeframeAggregationService, Depends(get_timeframe_aggregation_service)],
    payload: MultiTimeframeContextCreate | None = None,
) -> MultiTimeframeContextRead:
    resolved_payload = context_payload_or_default(payload)
    context = await service.build_context_for_analysis_run(
        analysis_run_id=analysis_run_id,
        context_timeframes=resolved_payload.context_timeframes,
        force_recompute=resolved_payload.force_recompute,
    )
    return MultiTimeframeContextRead.model_validate(context)


@router.get(
    "/analysis-runs/{analysis_run_id}/multi-timeframe-context",
    response_model=MultiTimeframeContextRead,
)
async def get_analysis_multi_timeframe_context(
    analysis_run_id: UUID,
    service: Annotated[TimeframeAggregationService, Depends(get_timeframe_aggregation_service)],
) -> MultiTimeframeContextRead:
    context = await service.get_context_for_analysis_run(analysis_run_id)
    return MultiTimeframeContextRead.model_validate(context)


@router.post(
    "/signals/{signal_id}/multi-timeframe-context",
    response_model=MultiTimeframeContextRead,
    status_code=status.HTTP_201_CREATED,
)
async def build_signal_multi_timeframe_context(
    signal_id: UUID,
    service: Annotated[TimeframeAggregationService, Depends(get_timeframe_aggregation_service)],
    payload: MultiTimeframeContextCreate | None = None,
) -> MultiTimeframeContextRead:
    resolved_payload = context_payload_or_default(payload)
    context = await service.build_context_for_signal(
        signal_id=signal_id,
        context_timeframes=resolved_payload.context_timeframes,
        force_recompute=resolved_payload.force_recompute,
    )
    return MultiTimeframeContextRead.model_validate(context)


@router.get("/signals/{signal_id}/multi-timeframe-context", response_model=MultiTimeframeContextRead)
async def get_signal_multi_timeframe_context(
    signal_id: UUID,
    service: Annotated[TimeframeAggregationService, Depends(get_timeframe_aggregation_service)],
) -> MultiTimeframeContextRead:
    context = await service.get_context_for_signal(signal_id)
    return MultiTimeframeContextRead.model_validate(context)
