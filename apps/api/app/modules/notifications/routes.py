from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.notifications.models import NotificationStatus
from app.modules.notifications.schemas import (
    NotificationCreateRequest,
    NotificationDispatchRequest,
    NotificationDispatchResponse,
    NotificationPreferenceRead,
    NotificationPreferenceUpsert,
    NotificationRead,
    NotificationWorkerStatusRead,
)
from app.modules.notifications.service import NotificationService

router = APIRouter(tags=["notifications"])


def get_notification_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> NotificationService:
    return NotificationService(session)


@router.put("/notifications/preferences", response_model=NotificationPreferenceRead)
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


@router.post("/notifications", response_model=NotificationRead)
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


@router.post("/notifications/dispatch-due", response_model=NotificationDispatchResponse)
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


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationRead:
    notification = await service.mark_read(notification_id)
    return NotificationRead.model_validate(notification)
