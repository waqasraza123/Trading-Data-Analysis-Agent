from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.candle_ingestion_performance.models import (
    CandleIngestionMode,
    CandleIngestionPerformanceStatus,
)
from app.modules.candle_ingestion_performance.schemas import (
    CandleIngestionConflictRead,
    CandleIngestionPerformanceRunListFilters,
    CandleIngestionPerformanceRunRead,
)
from app.modules.candle_ingestion_performance.service import (
    CandleIngestionPerformanceService,
)

router = APIRouter(prefix="/candle-ingestion", tags=["candle-ingestion"])


def get_candle_ingestion_performance_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> CandleIngestionPerformanceService:
    return CandleIngestionPerformanceService(session)


@router.get("/performance-runs", response_model=list[CandleIngestionPerformanceRunRead])
async def list_candle_ingestion_performance_runs(
    service: Annotated[
        CandleIngestionPerformanceService,
        Depends(get_candle_ingestion_performance_service),
    ],
    workspace_id: UUID,
    import_batch_id: UUID | None = None,
    provider_polling_request_id: UUID | None = None,
    source_id: UUID | None = None,
    symbol_id: UUID | None = None,
    ingestion_mode: CandleIngestionMode | None = None,
    status: Annotated[CandleIngestionPerformanceStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CandleIngestionPerformanceRunRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    runs = await service.list_runs(
        CandleIngestionPerformanceRunListFilters(
            workspace_id=workspace_id,
            import_batch_id=import_batch_id,
            provider_polling_request_id=provider_polling_request_id,
            source_id=source_id,
            symbol_id=symbol_id,
            ingestion_mode=ingestion_mode,
            status=status,
            limit=pagination.limit,
            offset=pagination.offset,
        )
    )
    return [CandleIngestionPerformanceRunRead.model_validate(run) for run in runs]


@router.get("/performance-runs/{run_id}", response_model=CandleIngestionPerformanceRunRead)
async def get_candle_ingestion_performance_run(
    run_id: UUID,
    service: Annotated[
        CandleIngestionPerformanceService,
        Depends(get_candle_ingestion_performance_service),
    ],
) -> CandleIngestionPerformanceRunRead:
    return CandleIngestionPerformanceRunRead.model_validate(await service.get_run(run_id))


@router.get(
    "/performance-runs/{run_id}/conflicts",
    response_model=list[CandleIngestionConflictRead],
)
async def list_candle_ingestion_performance_conflicts(
    run_id: UUID,
    service: Annotated[
        CandleIngestionPerformanceService,
        Depends(get_candle_ingestion_performance_service),
    ],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CandleIngestionConflictRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    conflicts = await service.list_conflicts(run_id, pagination.limit, pagination.offset)
    return [CandleIngestionConflictRead.model_validate(conflict) for conflict in conflicts]
