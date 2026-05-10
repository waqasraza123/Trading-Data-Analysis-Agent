from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.historical_cases.schemas import (
    HistoricalCaseBackfillRead,
    HistoricalCaseBackfillRequest,
    HistoricalCaseSearchRead,
    HistoricalCaseSearchRequest,
    HistoricalCaseVectorBuildRequest,
    HistoricalCaseVectorRead,
)
from app.modules.historical_cases.service import HistoricalCaseService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["historical-cases"])


def get_historical_case_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> HistoricalCaseService:
    return HistoricalCaseService(session)


@router.post(
    "/signals/{signal_id}/historical-case-vector",
    response_model=HistoricalCaseVectorRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def build_signal_historical_case_vector(
    signal_id: UUID,
    payload: HistoricalCaseVectorBuildRequest,
    service: Annotated[HistoricalCaseService, Depends(get_historical_case_service)],
) -> HistoricalCaseVectorRead:
    return await service.build_case_vector_for_signal(
        signal_id,
        force_recompute=payload.force_recompute,
    )


@router.get("/signals/{signal_id}/historical-case-vector", response_model=HistoricalCaseVectorRead)
async def get_signal_historical_case_vector(
    signal_id: UUID,
    service: Annotated[HistoricalCaseService, Depends(get_historical_case_service)],
) -> HistoricalCaseVectorRead:
    return await service.get_case_vector(signal_id)


@router.post(
    "/signals/{signal_id}/historical-cases/search",
    response_model=HistoricalCaseSearchRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def search_signal_historical_cases(
    signal_id: UUID,
    payload: HistoricalCaseSearchRequest,
    service: Annotated[HistoricalCaseService, Depends(get_historical_case_service)],
) -> HistoricalCaseSearchRead:
    return await service.search_similar_cases_for_signal(
        signal_id=signal_id,
        filters=payload.filters,
        limit=payload.limit,
    )


@router.post(
    "/analysis-runs/{analysis_run_id}/historical-cases/search",
    response_model=HistoricalCaseSearchRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def search_analysis_run_historical_cases(
    analysis_run_id: UUID,
    payload: HistoricalCaseSearchRequest,
    service: Annotated[HistoricalCaseService, Depends(get_historical_case_service)],
) -> HistoricalCaseSearchRead:
    return await service.search_similar_cases_for_analysis_run(
        analysis_run_id=analysis_run_id,
        filters=payload.filters,
        limit=payload.limit,
    )


@router.post(
    "/historical-cases/backfill",
    response_model=HistoricalCaseBackfillRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def backfill_historical_case_vectors(
    payload: HistoricalCaseBackfillRequest,
    service: Annotated[HistoricalCaseService, Depends(get_historical_case_service)],
) -> HistoricalCaseBackfillRead:
    return await service.backfill_case_vectors(
        workspace_id=payload.workspace_id,
        limit=payload.limit,
        force_recompute=payload.force_recompute,
    )
