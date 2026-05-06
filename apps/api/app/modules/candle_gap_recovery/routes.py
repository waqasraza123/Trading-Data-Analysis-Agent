from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.candle_gap_recovery.models import CandleGapRecoveryItemStatus
from app.modules.candle_gap_recovery.schemas import (
    CandleGapRecoveryItemListQuery,
    CandleGapRecoveryItemRead,
    CandleGapRecoveryPlanCreate,
    CandleGapRecoveryPlanRead,
    PrepareProviderPollingRequest,
    PrepareProviderPollingResponse,
)
from app.modules.candle_gap_recovery.service import CandleGapRecoveryService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/candle-gap-recovery", tags=["candle-gap-recovery"])


def get_candle_gap_recovery_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> CandleGapRecoveryService:
    return CandleGapRecoveryService(session)


@router.post(
    "/plans",
    response_model=CandleGapRecoveryPlanRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.PROVIDER_POLLING_WRITE))],
)
async def create_candle_gap_recovery_plan(
    payload: CandleGapRecoveryPlanCreate,
    service: Annotated[
        CandleGapRecoveryService,
        Depends(get_candle_gap_recovery_service),
    ],
) -> CandleGapRecoveryPlanRead:
    plan = await service.create_recovery_plan(payload)
    return CandleGapRecoveryPlanRead.model_validate(plan)


@router.get("/plans/{plan_id}", response_model=CandleGapRecoveryPlanRead)
async def get_candle_gap_recovery_plan(
    plan_id: UUID,
    service: Annotated[
        CandleGapRecoveryService,
        Depends(get_candle_gap_recovery_service),
    ],
) -> CandleGapRecoveryPlanRead:
    plan = await service.get_recovery_plan(plan_id)
    return CandleGapRecoveryPlanRead.model_validate(plan)


@router.get("/plans/{plan_id}/items", response_model=list[CandleGapRecoveryItemRead])
async def list_candle_gap_recovery_items(
    plan_id: UUID,
    service: Annotated[
        CandleGapRecoveryService,
        Depends(get_candle_gap_recovery_service),
    ],
    item_status: Annotated[CandleGapRecoveryItemStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CandleGapRecoveryItemRead]:
    items = await service.list_recovery_items(
        plan_id,
        CandleGapRecoveryItemListQuery(
            status=item_status,
            limit=limit,
            offset=offset,
        ),
    )
    return [CandleGapRecoveryItemRead.model_validate(item) for item in items]


@router.post(
    "/plans/{plan_id}/prepare-provider-polling",
    response_model=PrepareProviderPollingResponse,
    dependencies=[Depends(require_permission(Permission.PROVIDER_POLLING_WRITE))],
)
async def prepare_candle_gap_recovery_provider_polling(
    plan_id: UUID,
    payload: PrepareProviderPollingRequest,
    service: Annotated[
        CandleGapRecoveryService,
        Depends(get_candle_gap_recovery_service),
    ],
) -> PrepareProviderPollingResponse:
    return await service.prepare_provider_polling_requests(
        plan_id,
        create_requests=payload.create_requests,
    )


@router.post(
    "/plans/{plan_id}/cancel",
    response_model=CandleGapRecoveryPlanRead,
    dependencies=[Depends(require_permission(Permission.PROVIDER_POLLING_WRITE))],
)
async def cancel_candle_gap_recovery_plan(
    plan_id: UUID,
    service: Annotated[
        CandleGapRecoveryService,
        Depends(get_candle_gap_recovery_service),
    ],
) -> CandleGapRecoveryPlanRead:
    plan = await service.cancel_recovery_plan(plan_id)
    return CandleGapRecoveryPlanRead.model_validate(plan)
