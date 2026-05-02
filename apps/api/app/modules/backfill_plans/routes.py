from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.backfill_plans.models import BackfillItemStatus, BackfillPlanStatus, BackfillPlanType
from app.modules.backfill_plans.schemas import (
    BackfillItemListQuery,
    BackfillItemRead,
    BackfillPlanCreate,
    BackfillPlanListQuery,
    BackfillPlanRead,
)
from app.modules.backfill_plans.service import BackfillPlanService

router = APIRouter(prefix="/backfill-plans", tags=["backfill-plans"])


def get_backfill_plan_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> BackfillPlanService:
    return BackfillPlanService(session)


@router.post("", response_model=BackfillPlanRead, status_code=status.HTTP_201_CREATED)
async def create_backfill_plan(
    payload: BackfillPlanCreate,
    service: Annotated[BackfillPlanService, Depends(get_backfill_plan_service)],
) -> BackfillPlanRead:
    plan = await service.create_backfill_plan(payload)
    return BackfillPlanRead.model_validate(plan)


@router.get("", response_model=list[BackfillPlanRead])
async def list_backfill_plans(
    service: Annotated[BackfillPlanService, Depends(get_backfill_plan_service)],
    workspace_id: UUID,
    plan_type: BackfillPlanType | None = None,
    plan_status: Annotated[BackfillPlanStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BackfillPlanRead]:
    plans = await service.list_backfill_plans(
        BackfillPlanListQuery(
            workspace_id=workspace_id,
            plan_type=plan_type,
            status=plan_status,
            limit=limit,
            offset=offset,
        )
    )
    return [BackfillPlanRead.model_validate(plan) for plan in plans]


@router.get("/{plan_id}", response_model=BackfillPlanRead)
async def get_backfill_plan(
    plan_id: UUID,
    service: Annotated[BackfillPlanService, Depends(get_backfill_plan_service)],
) -> BackfillPlanRead:
    plan = await service.get_backfill_plan(plan_id)
    return BackfillPlanRead.model_validate(plan)


@router.get("/{plan_id}/items", response_model=list[BackfillItemRead])
async def list_backfill_items(
    plan_id: UUID,
    service: Annotated[BackfillPlanService, Depends(get_backfill_plan_service)],
    item_status: Annotated[BackfillItemStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BackfillItemRead]:
    items = await service.list_backfill_items(
        plan_id,
        BackfillItemListQuery(status=item_status, limit=limit, offset=offset),
    )
    return [BackfillItemRead.model_validate(item) for item in items]


@router.post("/{plan_id}/cancel", response_model=BackfillPlanRead)
async def cancel_backfill_plan(
    plan_id: UUID,
    service: Annotated[BackfillPlanService, Depends(get_backfill_plan_service)],
) -> BackfillPlanRead:
    plan = await service.cancel_backfill_plan(plan_id)
    return BackfillPlanRead.model_validate(plan)
