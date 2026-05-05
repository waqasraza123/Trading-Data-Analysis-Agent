from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.scanner_presets.models import ScannerPresetCategory
from app.modules.scanner_presets.schemas import (
    ScannerPresetApplicationRead,
    ScannerPresetApplyRequest,
    ScannerPresetRead,
    ScannerPresetSeedRead,
)
from app.modules.scanner_presets.service import ScannerPresetService

router = APIRouter(prefix="/scanner-presets", tags=["scanner-presets"])


def get_scanner_preset_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ScannerPresetService:
    return ScannerPresetService(session)


@router.get("", response_model=list[ScannerPresetRead])
async def list_scanner_presets(
    service: Annotated[ScannerPresetService, Depends(get_scanner_preset_service)],
    workspace_id: UUID | None = None,
    category: ScannerPresetCategory | None = None,
) -> list[ScannerPresetRead]:
    presets = await service.list_presets(workspace_id=workspace_id, category=category)
    return [ScannerPresetRead.model_validate(preset) for preset in presets]


@router.get("/{preset_key}", response_model=ScannerPresetRead)
async def get_scanner_preset(
    preset_key: str,
    service: Annotated[ScannerPresetService, Depends(get_scanner_preset_service)],
    workspace_id: UUID | None = None,
) -> ScannerPresetRead:
    preset = await service.get_preset(preset_key, workspace_id=workspace_id)
    return ScannerPresetRead.model_validate(preset)


@router.post(
    "/seed-default",
    response_model=ScannerPresetSeedRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.RUNTIME_ADMIN))],
)
async def seed_default_scanner_presets(
    service: Annotated[ScannerPresetService, Depends(get_scanner_preset_service)],
) -> ScannerPresetSeedRead:
    presets = await service.seed_default_presets()
    return ScannerPresetSeedRead(
        seeded_count=len(presets),
        presets=[ScannerPresetRead.model_validate(preset) for preset in presets],
    )


@router.post(
    "/{preset_id}/apply",
    response_model=ScannerPresetApplicationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def apply_scanner_preset(
    preset_id: UUID,
    payload: ScannerPresetApplyRequest,
    service: Annotated[ScannerPresetService, Depends(get_scanner_preset_service)],
    workspace_id: Annotated[UUID | None, Query()] = None,
) -> ScannerPresetApplicationRead:
    application = await service.apply_preset(
        workspace_id=workspace_id or payload.workspace_id,
        preset_id=preset_id,
        options=payload,
    )
    return ScannerPresetApplicationRead.model_validate(application)


@router.get(
    "/applications/{application_id}",
    response_model=ScannerPresetApplicationRead,
)
async def get_scanner_preset_application(
    application_id: UUID,
    service: Annotated[ScannerPresetService, Depends(get_scanner_preset_service)],
) -> ScannerPresetApplicationRead:
    application = await service.get_application(application_id)
    return ScannerPresetApplicationRead.model_validate(application)
