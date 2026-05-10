from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.webhook_outbox.models import (
    WebhookEventType,
    WebhookOutboxEventStatus,
    WebhookSubscriptionStatus,
)
from app.modules.webhook_outbox.schemas import (
    WebhookOutboxEventCreate,
    WebhookOutboxEventRead,
    WebhookSubscriptionCreate,
    WebhookSubscriptionRead,
    WebhookSubscriptionUpdate,
)
from app.modules.webhook_outbox.service import WebhookOutboxService

router = APIRouter(tags=["webhook-outbox"])


def get_webhook_outbox_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> WebhookOutboxService:
    return WebhookOutboxService(session)


@router.post(
    "/webhook-subscriptions",
    response_model=WebhookSubscriptionRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def create_webhook_subscription(
    payload: WebhookSubscriptionCreate,
    service: Annotated[WebhookOutboxService, Depends(get_webhook_outbox_service)],
) -> WebhookSubscriptionRead:
    subscription = await service.create_subscription(payload)
    return WebhookSubscriptionRead.model_validate(subscription)


@router.get("/webhook-subscriptions", response_model=list[WebhookSubscriptionRead])
async def list_webhook_subscriptions(
    service: Annotated[WebhookOutboxService, Depends(get_webhook_outbox_service)],
    workspace_id: UUID,
    status: WebhookSubscriptionStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WebhookSubscriptionRead]:
    subscriptions = await service.list_subscriptions(
        workspace_id=workspace_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [WebhookSubscriptionRead.model_validate(subscription) for subscription in subscriptions]


@router.get("/webhook-subscriptions/{subscription_id}", response_model=WebhookSubscriptionRead)
async def get_webhook_subscription(
    subscription_id: UUID,
    service: Annotated[WebhookOutboxService, Depends(get_webhook_outbox_service)],
) -> WebhookSubscriptionRead:
    subscription = await service.get_subscription(subscription_id)
    return WebhookSubscriptionRead.model_validate(subscription)


@router.patch(
    "/webhook-subscriptions/{subscription_id}",
    response_model=WebhookSubscriptionRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def update_webhook_subscription(
    subscription_id: UUID,
    payload: WebhookSubscriptionUpdate,
    service: Annotated[WebhookOutboxService, Depends(get_webhook_outbox_service)],
) -> WebhookSubscriptionRead:
    subscription = await service.update_subscription(subscription_id, payload)
    return WebhookSubscriptionRead.model_validate(subscription)


@router.post(
    "/webhook-subscriptions/{subscription_id}/archive",
    response_model=WebhookSubscriptionRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def archive_webhook_subscription(
    subscription_id: UUID,
    service: Annotated[WebhookOutboxService, Depends(get_webhook_outbox_service)],
) -> WebhookSubscriptionRead:
    subscription = await service.archive_subscription(subscription_id)
    return WebhookSubscriptionRead.model_validate(subscription)


@router.post(
    "/webhook-outbox/events",
    response_model=WebhookOutboxEventRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def create_webhook_outbox_event(
    payload: WebhookOutboxEventCreate,
    service: Annotated[WebhookOutboxService, Depends(get_webhook_outbox_service)],
) -> WebhookOutboxEventRead:
    event = await service.build_outbox_event(payload)
    return WebhookOutboxEventRead.model_validate(event)


@router.get("/webhook-outbox/events", response_model=list[WebhookOutboxEventRead])
async def list_webhook_outbox_events(
    service: Annotated[WebhookOutboxService, Depends(get_webhook_outbox_service)],
    workspace_id: UUID,
    event_type: WebhookEventType | None = None,
    status: WebhookOutboxEventStatus | None = None,
    source_type: str | None = None,
    source_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WebhookOutboxEventRead]:
    events = await service.list_outbox_events(
        workspace_id=workspace_id,
        event_type=event_type,
        status=status,
        source_type=source_type,
        source_id=source_id,
        limit=limit,
        offset=offset,
    )
    return [WebhookOutboxEventRead.model_validate(event) for event in events]


@router.get("/webhook-outbox/events/{event_id}", response_model=WebhookOutboxEventRead)
async def get_webhook_outbox_event(
    event_id: UUID,
    service: Annotated[WebhookOutboxService, Depends(get_webhook_outbox_service)],
) -> WebhookOutboxEventRead:
    event = await service.get_outbox_event(event_id)
    return WebhookOutboxEventRead.model_validate(event)


@router.post(
    "/webhook-outbox/events/{event_id}/cancel",
    response_model=WebhookOutboxEventRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def cancel_webhook_outbox_event(
    event_id: UUID,
    service: Annotated[WebhookOutboxService, Depends(get_webhook_outbox_service)],
) -> WebhookOutboxEventRead:
    event = await service.cancel_outbox_event(event_id)
    return WebhookOutboxEventRead.model_validate(event)
