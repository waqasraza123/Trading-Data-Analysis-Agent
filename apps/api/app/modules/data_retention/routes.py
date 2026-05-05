from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.data_retention.models import DataRetentionPolicyStatus
from app.modules.data_retention.schemas import (
    DataRetentionPolicyCreate,
    DataRetentionPolicyRead,
    DataRetentionPolicyUpdate,
    DataRetentionRunFilters,
    DataRetentionRunItemRead,
    DataRetentionRunRead,
)
from app.modules.data_retention.service import DataRetentionService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/data-retention", tags=["data-retention"])


def get_data_retention_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> DataRetentionService:
    return DataRetentionService(session)


@router.post(
    "/policies",
    response_model=DataRetentionPolicyRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.DATA_RETENTION_ADMIN))],
)
async def create_policy(
    payload: DataRetentionPolicyCreate,
    service: Annotated[DataRetentionService, Depends(get_data_retention_service)],
) -> DataRetentionPolicyRead:
    policy = await service.create_policy(payload)
    return DataRetentionPolicyRead.model_validate(policy)


@router.get("/policies", response_model=list[DataRetentionPolicyRead])
async def list_policies(
    service: Annotated[DataRetentionService, Depends(get_data_retention_service)],
    workspace_id: UUID,
    policy_status: Annotated[
        DataRetentionPolicyStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DataRetentionPolicyRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    policies = await service.list_policies(
        workspace_id=workspace_id,
        status=policy_status,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [DataRetentionPolicyRead.model_validate(policy) for policy in policies]


@router.get("/policies/{policy_id}", response_model=DataRetentionPolicyRead)
async def get_policy(
    policy_id: UUID,
    service: Annotated[DataRetentionService, Depends(get_data_retention_service)],
) -> DataRetentionPolicyRead:
    policy = await service.get_policy(policy_id)
    return DataRetentionPolicyRead.model_validate(policy)


@router.patch(
    "/policies/{policy_id}",
    response_model=DataRetentionPolicyRead,
    dependencies=[Depends(require_permission(Permission.DATA_RETENTION_ADMIN))],
)
async def update_policy(
    policy_id: UUID,
    payload: DataRetentionPolicyUpdate,
    service: Annotated[DataRetentionService, Depends(get_data_retention_service)],
) -> DataRetentionPolicyRead:
    policy = await service.update_policy(policy_id, payload)
    return DataRetentionPolicyRead.model_validate(policy)


@router.post(
    "/runs/dry-run",
    response_model=DataRetentionRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.DATA_RETENTION_ADMIN))],
)
async def create_dry_run(
    payload: DataRetentionRunFilters,
    service: Annotated[DataRetentionService, Depends(get_data_retention_service)],
) -> DataRetentionRunRead:
    run = await service.plan_retention_run(payload)
    return DataRetentionRunRead.model_validate(run)


@router.post(
    "/runs/{run_id}/apply",
    response_model=DataRetentionRunRead,
    dependencies=[Depends(require_permission(Permission.DATA_RETENTION_ADMIN))],
)
async def apply_run(
    run_id: UUID,
    service: Annotated[DataRetentionService, Depends(get_data_retention_service)],
) -> DataRetentionRunRead:
    run = await service.apply_retention_run(run_id)
    return DataRetentionRunRead.model_validate(run)


@router.get("/runs/{run_id}", response_model=DataRetentionRunRead)
async def get_run(
    run_id: UUID,
    service: Annotated[DataRetentionService, Depends(get_data_retention_service)],
) -> DataRetentionRunRead:
    run = await service.get_run(run_id)
    return DataRetentionRunRead.model_validate(run)


@router.get("/runs/{run_id}/items", response_model=list[DataRetentionRunItemRead])
async def list_run_items(
    run_id: UUID,
    service: Annotated[DataRetentionService, Depends(get_data_retention_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DataRetentionRunItemRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    items = await service.list_run_items(run_id, pagination.limit, pagination.offset)
    return [DataRetentionRunItemRead.model_validate(item) for item in items]
