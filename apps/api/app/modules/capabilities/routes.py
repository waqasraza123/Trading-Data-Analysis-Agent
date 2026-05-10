from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.capabilities.models import (
    CapabilityCategory,
    CapabilityExecutionType,
    CapabilitySafetyLevel,
    CapabilityStatus,
    IntelligenceCapability,
)
from app.modules.capabilities.schemas import (
    CapabilityListQuery,
    CapabilityRead,
    CapabilitySeedRead,
    CapabilitySummaryRead,
)
from app.modules.capabilities.service import CapabilityService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


def get_capability_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> CapabilityService:
    return CapabilityService(session)


def capability_read(
    capability: IntelligenceCapability,
    service: CapabilityService,
    include_runtime: bool,
) -> CapabilityRead:
    response = CapabilityRead.model_validate(capability)
    if include_runtime:
        response.runtime_availability = service.runtime_for_capability(capability)
    return response


@router.get("", response_model=list[CapabilityRead])
async def list_capabilities(
    service: Annotated[CapabilityService, Depends(get_capability_service)],
    category: CapabilityCategory | None = None,
    status_filter: Annotated[CapabilityStatus | None, Query(alias="status")] = None,
    execution_type: CapabilityExecutionType | None = None,
    safety_level: CapabilitySafetyLevel | None = None,
    requires_external_credentials: bool | None = None,
    include_runtime: bool = True,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[CapabilityRead]:
    query = CapabilityListQuery(
        category=category,
        status=status_filter,
        execution_type=execution_type,
        safety_level=safety_level,
        requires_external_credentials=requires_external_credentials,
        include_runtime=include_runtime,
        limit=limit,
        offset=offset,
    )
    capabilities = await service.list_capabilities(
        category=query.category.value if query.category is not None else None,
        status=query.status.value if query.status is not None else None,
        execution_type=query.execution_type.value if query.execution_type is not None else None,
        safety_level=query.safety_level.value if query.safety_level is not None else None,
        requires_external_credentials=query.requires_external_credentials,
        limit=query.limit,
        offset=query.offset,
    )
    return [
        capability_read(capability, service, query.include_runtime) for capability in capabilities
    ]


@router.get("/summary", response_model=CapabilitySummaryRead)
async def summarize_capabilities(
    service: Annotated[CapabilityService, Depends(get_capability_service)],
) -> CapabilitySummaryRead:
    return await service.summarize_capabilities()


@router.get("/{key}", response_model=CapabilityRead)
async def get_capability(
    key: str,
    service: Annotated[CapabilityService, Depends(get_capability_service)],
    include_runtime: bool = True,
) -> CapabilityRead:
    capability = await service.get_capability(key)
    return capability_read(capability, service, include_runtime)


@router.post(
    "/seed-default",
    response_model=CapabilitySeedRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.RUNTIME_ADMIN))],
)
async def seed_default_capabilities(
    service: Annotated[CapabilityService, Depends(get_capability_service)],
) -> CapabilitySeedRead:
    result = await service.seed_default_capabilities()
    await service.session.commit()
    return CapabilitySeedRead(
        seeded_count=len(result.capabilities),
        capability_keys=[
            f"{capability.key}.{capability.version}" for capability in result.capabilities
        ],
    )
