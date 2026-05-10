from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.confidence_calibration.schemas import (
    ConfidenceCalibrationBinRead,
    ConfidenceCalibrationRunRead,
    ConfidenceCalibrationRunRequest,
)
from app.modules.confidence_calibration.service import ConfidenceCalibrationService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/confidence-calibration", tags=["confidence-calibration"])


def get_confidence_calibration_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ConfidenceCalibrationService:
    return ConfidenceCalibrationService(session)


@router.post(
    "/run",
    response_model=ConfidenceCalibrationRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def run_confidence_calibration(
    payload: ConfidenceCalibrationRunRequest,
    service: Annotated[
        ConfidenceCalibrationService,
        Depends(get_confidence_calibration_service),
    ],
) -> ConfidenceCalibrationRunRead:
    run = await service.run_calibration(payload)
    return ConfidenceCalibrationRunRead.model_validate(run)


@router.get("/runs", response_model=list[ConfidenceCalibrationRunRead])
async def list_confidence_calibration_runs(
    service: Annotated[
        ConfidenceCalibrationService,
        Depends(get_confidence_calibration_service),
    ],
    workspace_id: UUID,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ConfidenceCalibrationRunRead]:
    runs = await service.list_runs(
        workspace_id=workspace_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [ConfidenceCalibrationRunRead.model_validate(run) for run in runs]


@router.get("/runs/{run_id}", response_model=ConfidenceCalibrationRunRead)
async def get_confidence_calibration_run(
    run_id: UUID,
    service: Annotated[
        ConfidenceCalibrationService,
        Depends(get_confidence_calibration_service),
    ],
) -> ConfidenceCalibrationRunRead:
    run = await service.get_run(run_id)
    return ConfidenceCalibrationRunRead.model_validate(run)


@router.get("/runs/{run_id}/bins", response_model=list[ConfidenceCalibrationBinRead])
async def list_confidence_calibration_bins(
    run_id: UUID,
    service: Annotated[
        ConfidenceCalibrationService,
        Depends(get_confidence_calibration_service),
    ],
    horizon_minutes: Annotated[int | None, Query(gt=0)] = None,
    calibration_label: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ConfidenceCalibrationBinRead]:
    bins = await service.list_bins(
        run_id=run_id,
        horizon_minutes=horizon_minutes,
        calibration_label=calibration_label,
        limit=limit,
        offset=offset,
    )
    return [
        ConfidenceCalibrationBinRead.model_validate(calibration_bin) for calibration_bin in bins
    ]
