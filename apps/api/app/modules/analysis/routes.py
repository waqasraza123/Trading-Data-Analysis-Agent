from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.analysis.models import AnalysisMode, AnalysisRunStatus
from app.modules.analysis.schemas import (
    AnalysisAuditLogRead,
    AnalysisRunCreate,
    AnalysisRunRead,
    LiveWindowAnalysisRunCreate,
)
from app.modules.analysis.service import AnalysisService

router = APIRouter(prefix="/analysis-runs", tags=["analysis-runs"])


def get_analysis_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AnalysisService:
    return AnalysisService(session)


@router.post("", response_model=AnalysisRunRead, status_code=status.HTTP_201_CREATED)
async def create_analysis_run(
    payload: AnalysisRunCreate,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRunRead:
    run = await service.create_historical_run(payload)
    return AnalysisRunRead.model_validate(run)


@router.post("/live-window", response_model=AnalysisRunRead, status_code=status.HTTP_201_CREATED)
async def create_live_window_analysis_run(
    payload: LiveWindowAnalysisRunCreate,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRunRead:
    run = await service.create_live_window_run(payload)
    return AnalysisRunRead.model_validate(run)


@router.get("", response_model=list[AnalysisRunRead])
async def list_analysis_runs(
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
    symbol_id: UUID | None = None,
    status_filter: Annotated[AnalysisRunStatus | None, Query(alias="status")] = None,
    analysis_mode: AnalysisMode | None = None,
) -> list[AnalysisRunRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    runs = await service.list_runs(
        limit=pagination.limit,
        offset=pagination.offset,
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        status=status_filter.value if status_filter else None,
        analysis_mode=analysis_mode.value if analysis_mode else None,
    )
    return [AnalysisRunRead.model_validate(run) for run in runs]


@router.get("/{analysis_run_id}", response_model=AnalysisRunRead)
async def get_analysis_run(
    analysis_run_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRunRead:
    run = await service.get_run(analysis_run_id)
    return AnalysisRunRead.model_validate(run)


@router.get("/{analysis_run_id}/audit-logs", response_model=list[AnalysisAuditLogRead])
async def list_analysis_audit_logs(
    analysis_run_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> list[AnalysisAuditLogRead]:
    audit_logs = await service.list_audit_logs(analysis_run_id)
    return [AnalysisAuditLogRead.model_validate(audit_log) for audit_log in audit_logs]


@router.post("/{analysis_run_id}/retry", response_model=AnalysisRunRead)
async def retry_analysis_run(
    analysis_run_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRunRead:
    run = await service.retry_run(analysis_run_id)
    return AnalysisRunRead.model_validate(run)
