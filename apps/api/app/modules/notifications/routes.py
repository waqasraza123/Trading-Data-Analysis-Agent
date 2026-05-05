from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.notifications.models import (
    BackendNotificationEventType,
    NotificationChannelStatus,
    NotificationDeliveryChannelType,
    NotificationEventSeverity,
    NotificationEventStatus,
    NotificationInboxStatus,
    NotificationStatus,
)
from app.modules.notifications.schemas import (
    NotificationChannelCreate,
    NotificationChannelRead,
    NotificationChannelUpdate,
    NotificationCreateRequest,
    NotificationDeliveryAttemptRead,
    NotificationDeliveryResponse,
    NotificationDispatchRequest,
    NotificationDispatchResponse,
    NotificationEventAcknowledgeRequest,
    NotificationEventCreate,
    NotificationEventRead,
    NotificationPreferenceRead,
    NotificationPreferenceUpsert,
    NotificationRead,
    NotificationWorkerStatusRead,
)
from app.modules.notifications.service import NotificationService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["notifications"])


def get_notification_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> NotificationService:
    return NotificationService(session)


@router.put(
    "/notifications/preferences",
    response_model=NotificationPreferenceRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def upsert_notification_preference(
    payload: NotificationPreferenceUpsert,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationPreferenceRead:
    preference = await service.upsert_preference(payload)
    return NotificationPreferenceRead.model_validate(preference)


@router.get("/notifications/preferences", response_model=list[NotificationPreferenceRead])
async def list_notification_preferences(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    workspace_id: UUID,
    user_id: UUID | None = None,
) -> list[NotificationPreferenceRead]:
    preferences = await service.list_preferences(workspace_id=workspace_id, user_id=user_id)
    return [NotificationPreferenceRead.model_validate(preference) for preference in preferences]


@router.post(
    "/notification-channels",
    response_model=NotificationChannelRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def create_notification_channel(
    payload: NotificationChannelCreate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationChannelRead:
    channel = await service.create_channel(payload)
    return NotificationChannelRead.model_validate(channel)


@router.get("/notification-channels", response_model=list[NotificationChannelRead])
async def list_notification_channels(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    workspace_id: UUID,
    status: NotificationChannelStatus | None = None,
    channel_type: NotificationDeliveryChannelType | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NotificationChannelRead]:
    channels = await service.list_channels(
        workspace_id=workspace_id,
        status=status,
        channel_type=channel_type,
        limit=limit,
        offset=offset,
    )
    return [NotificationChannelRead.model_validate(channel) for channel in channels]


@router.get("/notification-channels/{channel_id}", response_model=NotificationChannelRead)
async def get_notification_channel(
    channel_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationChannelRead:
    channel = await service.get_channel(channel_id)
    return NotificationChannelRead.model_validate(channel)


@router.patch(
    "/notification-channels/{channel_id}",
    response_model=NotificationChannelRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def update_notification_channel(
    channel_id: UUID,
    payload: NotificationChannelUpdate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationChannelRead:
    channel = await service.update_channel(channel_id, payload)
    return NotificationChannelRead.model_validate(channel)


@router.post(
    "/notification-channels/{channel_id}/archive",
    response_model=NotificationChannelRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def archive_notification_channel(
    channel_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationChannelRead:
    channel = await service.archive_channel(channel_id)
    return NotificationChannelRead.model_validate(channel)


@router.post(
    "/notification-events",
    response_model=NotificationEventRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def create_notification_event(
    payload: NotificationEventCreate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationEventRead:
    event = await service.create_notification_event(payload)
    return NotificationEventRead.model_validate(event)


@router.get("/notification-events", response_model=list[NotificationEventRead])
async def list_notification_events(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    workspace_id: UUID,
    event_type: BackendNotificationEventType | None = None,
    status: NotificationEventStatus | None = None,
    severity: NotificationEventSeverity | None = None,
    source_type: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    inbox_status: NotificationInboxStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NotificationEventRead]:
    events = await service.list_notification_events(
        workspace_id=workspace_id,
        event_type=event_type,
        status=status,
        severity=severity,
        source_type=source_type,
        inbox_status=inbox_status,
        limit=limit,
        offset=offset,
    )
    return [NotificationEventRead.model_validate(event) for event in events]


@router.get("/notification-events/{event_id}", response_model=NotificationEventRead)
async def get_notification_event(
    event_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationEventRead:
    event = await service.get_notification_event(event_id)
    return NotificationEventRead.model_validate(event)


@router.post(
    "/notification-events/{event_id}/read",
    response_model=NotificationEventRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def mark_notification_event_read(
    event_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationEventRead:
    event = await service.mark_notification_event_read(event_id)
    return NotificationEventRead.model_validate(event)


@router.post(
    "/notification-events/{event_id}/acknowledge",
    response_model=NotificationEventRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def acknowledge_notification_event(
    event_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    payload: NotificationEventAcknowledgeRequest | None = None,
) -> NotificationEventRead:
    event = await service.acknowledge_notification_event(
        event_id,
        user_id=payload.user_id if payload is not None else None,
    )
    return NotificationEventRead.model_validate(event)


@router.post(
    "/notification-events/{event_id}/archive",
    response_model=NotificationEventRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def archive_notification_event(
    event_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationEventRead:
    event = await service.archive_notification_event(event_id)
    return NotificationEventRead.model_validate(event)


@router.post(
    "/notification-events/{event_id}/deliver",
    response_model=NotificationDeliveryResponse,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def deliver_notification_event(
    event_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationDeliveryResponse:
    return await service.deliver_notification_event(event_id)


@router.get(
    "/notification-events/{event_id}/attempts",
    response_model=list[NotificationDeliveryAttemptRead],
)
async def list_notification_delivery_attempts(
    event_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> list[NotificationDeliveryAttemptRead]:
    attempts = await service.list_delivery_attempts(event_id)
    return [NotificationDeliveryAttemptRead.model_validate(attempt) for attempt in attempts]


@router.post(
    "/notifications",
    response_model=NotificationRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def queue_notification(
    payload: NotificationCreateRequest,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationRead:
    notification = await service.queue_notification(payload)
    return NotificationRead.model_validate(notification)


@router.get("/notifications", response_model=list[NotificationRead])
async def list_notifications(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    workspace_id: UUID,
    user_id: UUID | None = None,
    status: NotificationStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NotificationRead]:
    notifications = await service.list_notifications(
        workspace_id=workspace_id,
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [NotificationRead.model_validate(notification) for notification in notifications]


@router.post(
    "/notifications/dispatch-due",
    response_model=NotificationDispatchResponse,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def dispatch_due_notifications(
    payload: NotificationDispatchRequest,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationDispatchResponse:
    return await service.dispatch_due_notifications(
        workspace_id=payload.workspace_id,
        limit=payload.limit,
    )


@router.get("/notifications/worker/status", response_model=NotificationWorkerStatusRead)
async def get_notification_worker_status(
    service: Annotated[NotificationService, Depends(get_notification_service)],
    workspace_id: UUID | None = None,
) -> NotificationWorkerStatusRead:
    return await service.worker_status(workspace_id=workspace_id)


@router.get("/notifications/{notification_id}", response_model=NotificationRead)
async def get_notification(
    notification_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationRead:
    notification = await service.get_notification(notification_id)
    return NotificationRead.model_validate(notification)


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationRead,
    dependencies=[Depends(require_permission(Permission.NOTIFICATIONS_WRITE))],
)
async def mark_notification_read(
    notification_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationRead:
    notification = await service.mark_read(notification_id)
    return NotificationRead.model_validate(notification)
