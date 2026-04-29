from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.live.heartbeat import LiveStalePolicy
from app.modules.live.models import LiveFeedSubscriptionStatus
from app.modules.live.schemas import (
    LiveFeedEventRead,
    LiveProviderMessage,
    LiveSubscriptionCreate,
    LiveSubscriptionRead,
    LiveSubscriptionStaleCheckRead,
    LiveSubscriptionStaleCheckRequest,
    LiveSubscriptionUpdate,
)
from app.modules.live.service import LiveService

router = APIRouter(prefix="/live", tags=["live"])


def get_live_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> LiveService:
    return LiveService(session)


@router.post(
    "/subscriptions",
    response_model=LiveSubscriptionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    payload: LiveSubscriptionCreate,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSubscriptionRead:
    subscription = await service.create_subscription(payload)
    return LiveSubscriptionRead.model_validate(subscription)


@router.get("/subscriptions", response_model=list[LiveSubscriptionRead])
async def list_subscriptions(
    service: Annotated[LiveService, Depends(get_live_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
    status_filter: Annotated[LiveFeedSubscriptionStatus | None, Query(alias="status")] = None,
    provider: str | None = None,
    symbol_id: UUID | None = None,
) -> list[LiveSubscriptionRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    subscriptions = await service.list_subscriptions(
        limit=pagination.limit,
        offset=pagination.offset,
        workspace_id=workspace_id,
        status=status_filter.value if status_filter else None,
        provider=provider.lower() if provider else None,
        symbol_id=symbol_id,
    )
    return [LiveSubscriptionRead.model_validate(subscription) for subscription in subscriptions]


@router.post("/subscriptions/stale-check", response_model=LiveSubscriptionStaleCheckRead)
async def refresh_stale_statuses(
    payload: LiveSubscriptionStaleCheckRequest,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSubscriptionStaleCheckRead:
    stale_count = await service.refresh_stale_statuses(
        workspace_id=payload.workspace_id,
        policy=LiveStalePolicy(
            message_stale_after_seconds=payload.message_stale_after_seconds,
            final_candle_stale_after_seconds=payload.final_candle_stale_after_seconds,
        ),
    )
    return LiveSubscriptionStaleCheckRead(stale_count=stale_count)


@router.get("/subscriptions/{subscription_id}", response_model=LiveSubscriptionRead)
async def get_subscription(
    subscription_id: UUID,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSubscriptionRead:
    subscription = await service.get_subscription(subscription_id)
    return LiveSubscriptionRead.model_validate(subscription)


@router.patch("/subscriptions/{subscription_id}", response_model=LiveSubscriptionRead)
async def update_subscription(
    subscription_id: UUID,
    payload: LiveSubscriptionUpdate,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSubscriptionRead:
    subscription = await service.update_subscription(subscription_id, payload)
    return LiveSubscriptionRead.model_validate(subscription)


@router.post("/subscriptions/{subscription_id}/pause", response_model=LiveSubscriptionRead)
async def pause_subscription(
    subscription_id: UUID,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSubscriptionRead:
    subscription = await service.pause_subscription(subscription_id)
    return LiveSubscriptionRead.model_validate(subscription)


@router.post("/subscriptions/{subscription_id}/resume", response_model=LiveSubscriptionRead)
async def resume_subscription(
    subscription_id: UUID,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSubscriptionRead:
    subscription = await service.resume_subscription(subscription_id)
    return LiveSubscriptionRead.model_validate(subscription)


@router.post("/subscriptions/{subscription_id}/stop", response_model=LiveSubscriptionRead)
async def stop_subscription(
    subscription_id: UUID,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSubscriptionRead:
    subscription = await service.stop_subscription_runtime(subscription_id)
    return LiveSubscriptionRead.model_validate(subscription)


@router.post(
    "/subscriptions/{subscription_id}/events",
    response_model=LiveFeedEventRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_provider_message(
    subscription_id: UUID,
    payload: LiveProviderMessage,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveFeedEventRead:
    event = await service.ingest_provider_message(subscription_id, payload)
    return LiveFeedEventRead.model_validate(event)


@router.get("/subscriptions/{subscription_id}/events", response_model=list[LiveFeedEventRead])
async def list_subscription_events(
    subscription_id: UUID,
    service: Annotated[LiveService, Depends(get_live_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LiveFeedEventRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    events = await service.list_subscription_events(
        subscription_id=subscription_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [LiveFeedEventRead.model_validate(event) for event in events]
