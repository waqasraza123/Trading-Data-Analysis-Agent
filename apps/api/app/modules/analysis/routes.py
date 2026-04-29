from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
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
from app.modules.features.schemas import FeatureSnapshotRead
from app.modules.indicators.schemas import IndicatorSnapshotRead
from app.modules.patterns.schemas import PatternCandidateRead

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


@router.get("/{analysis_run_id}/features", response_model=FeatureSnapshotRead)
async def get_analysis_features(
    analysis_run_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> FeatureSnapshotRead:
    snapshot = await service.get_feature_snapshot(analysis_run_id)
    if snapshot is None:
        raise AppError(404, "feature_snapshot_not_found", "Feature snapshot not found")
    return FeatureSnapshotRead.model_validate(snapshot)


@router.get("/{analysis_run_id}/indicators", response_model=IndicatorSnapshotRead)
async def get_analysis_indicators(
    analysis_run_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> IndicatorSnapshotRead:
    snapshot = await service.get_indicator_snapshot(analysis_run_id)
    if snapshot is None:
        raise AppError(404, "indicator_snapshot_not_found", "Indicator snapshot not found")
    return IndicatorSnapshotRead.model_validate(snapshot)


@router.get("/{analysis_run_id}/patterns", response_model=list[PatternCandidateRead])
async def list_analysis_patterns(
    analysis_run_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> list[PatternCandidateRead]:
    candidates = await service.list_pattern_candidates(analysis_run_id)
    return [PatternCandidateRead.model_validate(candidate) for candidate in candidates]


@router.post("/{analysis_run_id}/retry", response_model=AnalysisRunRead)
async def retry_analysis_run(
    analysis_run_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisRunRead:
    run = await service.retry_run(analysis_run_id)
    return AnalysisRunRead.model_validate(run)
