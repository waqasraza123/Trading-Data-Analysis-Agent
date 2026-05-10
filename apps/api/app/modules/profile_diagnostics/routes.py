from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.profile_diagnostics.schemas import (
    CalibrationRecommendationRead,
    CalibrationRecommendationStatusUpdate,
    PatternOutcomeDiagnosticRead,
    ProfileDiagnosticRunRequest,
    StrategyProfileDiagnosticRead,
    StrategyProfileDiagnosticRunRead,
)
from app.modules.profile_diagnostics.service import ProfileDiagnosticService

router = APIRouter(prefix="/profile-diagnostics", tags=["profile-diagnostics"])


def get_profile_diagnostic_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ProfileDiagnosticService:
    return ProfileDiagnosticService(session)


@router.post(
    "/run",
    response_model=StrategyProfileDiagnosticRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def run_profile_diagnostics(
    payload: ProfileDiagnosticRunRequest,
    service: Annotated[ProfileDiagnosticService, Depends(get_profile_diagnostic_service)],
) -> StrategyProfileDiagnosticRunRead:
    run = await service.run_workspace_diagnostics(payload)
    return StrategyProfileDiagnosticRunRead.model_validate(run)


@router.get("/runs/{run_id}", response_model=StrategyProfileDiagnosticRunRead)
async def get_profile_diagnostic_run(
    run_id: UUID,
    service: Annotated[ProfileDiagnosticService, Depends(get_profile_diagnostic_service)],
) -> StrategyProfileDiagnosticRunRead:
    run = await service.get_diagnostic_run(run_id)
    return StrategyProfileDiagnosticRunRead.model_validate(run)


@router.get("/strategy-profiles", response_model=list[StrategyProfileDiagnosticRead])
async def list_strategy_profile_diagnostics(
    service: Annotated[ProfileDiagnosticService, Depends(get_profile_diagnostic_service)],
    workspace_id: UUID,
    diagnostic_run_id: UUID | None = None,
    strategy_profile_key: str | None = None,
    symbol_id: UUID | None = None,
    timeframe: str | None = None,
    horizon_minutes: Annotated[int | None, Query(gt=0)] = None,
    diagnostic_label: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[StrategyProfileDiagnosticRead]:
    diagnostics = await service.list_strategy_profile_diagnostics(
        workspace_id=workspace_id,
        diagnostic_run_id=diagnostic_run_id,
        strategy_profile_key=strategy_profile_key,
        symbol_id=symbol_id,
        timeframe=timeframe,
        horizon_minutes=horizon_minutes,
        diagnostic_label=diagnostic_label,
        limit=limit,
        offset=offset,
    )
    return [StrategyProfileDiagnosticRead.model_validate(item) for item in diagnostics]


@router.get("/patterns", response_model=list[PatternOutcomeDiagnosticRead])
async def list_pattern_diagnostics(
    service: Annotated[ProfileDiagnosticService, Depends(get_profile_diagnostic_service)],
    workspace_id: UUID,
    diagnostic_run_id: UUID | None = None,
    pattern_type: str | None = None,
    strategy_profile_key: str | None = None,
    symbol_id: UUID | None = None,
    timeframe: str | None = None,
    horizon_minutes: Annotated[int | None, Query(gt=0)] = None,
    diagnostic_label: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PatternOutcomeDiagnosticRead]:
    diagnostics = await service.list_pattern_diagnostics(
        workspace_id=workspace_id,
        diagnostic_run_id=diagnostic_run_id,
        pattern_type=pattern_type,
        strategy_profile_key=strategy_profile_key,
        symbol_id=symbol_id,
        timeframe=timeframe,
        horizon_minutes=horizon_minutes,
        diagnostic_label=diagnostic_label,
        limit=limit,
        offset=offset,
    )
    return [PatternOutcomeDiagnosticRead.model_validate(item) for item in diagnostics]


@router.get("/recommendations", response_model=list[CalibrationRecommendationRead])
async def list_calibration_recommendations(
    service: Annotated[ProfileDiagnosticService, Depends(get_profile_diagnostic_service)],
    workspace_id: UUID,
    diagnostic_run_id: UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    recommendation_type: str | None = None,
    strategy_profile_key: str | None = None,
    pattern_type: str | None = None,
    symbol_id: UUID | None = None,
    timeframe: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CalibrationRecommendationRead]:
    recommendations = await service.list_calibration_recommendations(
        workspace_id=workspace_id,
        diagnostic_run_id=diagnostic_run_id,
        status=status,
        severity=severity,
        recommendation_type=recommendation_type,
        strategy_profile_key=strategy_profile_key,
        pattern_type=pattern_type,
        symbol_id=symbol_id,
        timeframe=timeframe,
        limit=limit,
        offset=offset,
    )
    return [CalibrationRecommendationRead.model_validate(item) for item in recommendations]


@router.patch(
    "/recommendations/{recommendation_id}",
    response_model=CalibrationRecommendationRead,
    dependencies=[Depends(require_permission(Permission.STRATEGY_PROFILES_ADMIN))],
)
async def update_calibration_recommendation_status(
    recommendation_id: UUID,
    payload: CalibrationRecommendationStatusUpdate,
    service: Annotated[ProfileDiagnosticService, Depends(get_profile_diagnostic_service)],
) -> CalibrationRecommendationRead:
    recommendation = await service.update_recommendation_status(
        recommendation_id=recommendation_id,
        status=payload.status,
    )
    return CalibrationRecommendationRead.model_validate(recommendation)
