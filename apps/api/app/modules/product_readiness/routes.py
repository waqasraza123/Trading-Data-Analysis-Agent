from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.product_readiness.models import (
    ProductReadinessLabel,
    ProductReadinessRunStatus,
)
from app.modules.product_readiness.repository import ProductReadinessRepository
from app.modules.product_readiness.schemas import (
    ProductReadinessRunListResponse,
    ProductReadinessRunRead,
    ProductReadinessRunRequest,
)
from app.modules.product_readiness.service import ProductReadinessService

router = APIRouter(prefix="/product-readiness", tags=["product-readiness"])


def get_product_readiness_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ProductReadinessService:
    return ProductReadinessService(ProductReadinessRepository(session))


@router.post(
    "/run",
    response_model=ProductReadinessRunRead,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def run_product_readiness_check(
    service: Annotated[ProductReadinessService, Depends(get_product_readiness_service)],
    payload: ProductReadinessRunRequest | None = None,
    workspace_id: Annotated[UUID | None, Query(alias="workspaceId")] = None,
) -> ProductReadinessRunRead:
    selected_workspace_id = (
        workspace_id if workspace_id is not None else payload.workspace_id if payload else None
    )
    return await service.run_readiness_check(selected_workspace_id)


@router.get("/latest", response_model=ProductReadinessRunRead)
async def get_latest_product_readiness(
    service: Annotated[ProductReadinessService, Depends(get_product_readiness_service)],
    workspace_id: Annotated[UUID | None, Query(alias="workspaceId")] = None,
) -> ProductReadinessRunRead:
    return await service.get_latest_readiness(workspace_id)


@router.get("/runs", response_model=ProductReadinessRunListResponse)
async def list_product_readiness_runs(
    service: Annotated[ProductReadinessService, Depends(get_product_readiness_service)],
    workspace_id: Annotated[UUID | None, Query(alias="workspaceId")] = None,
    readiness_label: Annotated[
        ProductReadinessLabel | None,
        Query(alias="readinessLabel"),
    ] = None,
    status: ProductReadinessRunStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductReadinessRunListResponse:
    pagination = PaginationParams(limit=limit, offset=offset)
    return await service.list_readiness_runs(
        workspace_id=workspace_id,
        limit=pagination.limit,
        offset=pagination.offset,
        readiness_label=readiness_label.value if readiness_label is not None else None,
        status=status.value if status is not None else None,
    )


@router.get("/runs/{run_id}", response_model=ProductReadinessRunRead)
async def get_product_readiness_run(
    run_id: UUID,
    service: Annotated[ProductReadinessService, Depends(get_product_readiness_service)],
) -> ProductReadinessRunRead:
    return await service.get_readiness_run(run_id)
