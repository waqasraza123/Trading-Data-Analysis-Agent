from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.engine_versions.schemas import EngineVersionRead, EngineVersionSeedRead
from app.modules.engine_versions.service import EngineVersionService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/engine-versions", tags=["engine-versions"])


def get_engine_version_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> EngineVersionService:
    return EngineVersionService(session)


@router.get("", response_model=list[EngineVersionRead])
async def list_engine_versions(
    service: Annotated[EngineVersionService, Depends(get_engine_version_service)],
) -> list[EngineVersionRead]:
    versions = await service.list_versions()
    return [EngineVersionRead.model_validate(version) for version in versions]


@router.get("/{engine_name}", response_model=list[EngineVersionRead])
async def list_engine_versions_by_name(
    engine_name: str,
    service: Annotated[EngineVersionService, Depends(get_engine_version_service)],
) -> list[EngineVersionRead]:
    versions = await service.list_by_engine_name(engine_name)
    return [EngineVersionRead.model_validate(version) for version in versions]


@router.post(
    "/seed",
    response_model=EngineVersionSeedRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.RUNTIME_ADMIN))],
)
async def seed_engine_versions(
    service: Annotated[EngineVersionService, Depends(get_engine_version_service)],
) -> EngineVersionSeedRead:
    versions = await service.seed_current_versions()
    await service.session.commit()
    return EngineVersionSeedRead(
        seeded_count=len(versions),
        engine_names=[version.engine_name for version in versions],
    )
