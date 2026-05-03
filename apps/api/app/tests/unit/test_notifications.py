from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from app.config import AppEnvironment, Settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.notifications.models import (
    BackendNotificationEventType,
    NotificationChannel,
    NotificationEvent,
    NotificationEventSeverity,
    NotificationEventType,
    NotificationInboxStatus,
    NotificationMessage,
    NotificationPreference,
    NotificationSeverity,
    NotificationSourceType,
    NotificationStatus,
    NotificationWorkerRun,
)
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import (
    NotificationCreateRequest,
    NotificationEventCreate,
    NotificationPreferenceUpsert,
)
from app.modules.notifications.service import NotificationService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeNotificationRepository:
    def __init__(self) -> None:
        self.messages: dict[UUID, NotificationMessage] = {}
        self.events: dict[UUID, NotificationEvent] = {}
        self.messages_by_key: dict[tuple[UUID, str], NotificationMessage] = {}
        self.preferences: dict[tuple[UUID, UUID, str, str], NotificationPreference] = {}
        self.worker_runs: list[NotificationWorkerRun] = []

    async def upsert_preference(
        self,
        preference: NotificationPreference,
    ) -> NotificationPreference:
        self.ensure_preference_fields(preference)
        self.preferences[
            (
                preference.workspace_id,
                preference.user_id,
                preference.channel,
                preference.event_type,
            )
        ] = preference
        return preference

    async def get_preference(
        self,
        workspace_id: UUID,
        user_id: UUID,
        channel: str,
        event_type: str,
    ) -> NotificationPreference | None:
        return self.preferences.get((workspace_id, user_id, channel, event_type))

    async def list_preferences(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
    ) -> list[NotificationPreference]:
        return [
            preference
            for preference in self.preferences.values()
            if preference.workspace_id == workspace_id
            and (user_id is None or preference.user_id == user_id)
        ]

    async def create_message(self, message: NotificationMessage) -> NotificationMessage:
        self.ensure_message_fields(message)
        self.messages[message.id] = message
        self.messages_by_key[(message.workspace_id, message.idempotency_key)] = message
        return message

    async def get_message(self, message_id: UUID) -> NotificationMessage | None:
        return self.messages.get(message_id)

    async def get_message_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str,
    ) -> NotificationMessage | None:
        return self.messages_by_key.get((workspace_id, idempotency_key))

    async def list_messages(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
        status: NotificationStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationMessage]:
        rows = [
            message
            for message in self.messages.values()
            if message.workspace_id == workspace_id
            and (user_id is None or message.user_id == user_id)
            and (status is None or message.status == status.value)
        ]
        return rows[offset : offset + limit]

    async def claim_due_messages(
        self,
        now: datetime,
        worker_id: str,
        limit: int,
        lock_seconds: int,
        max_attempts: int,
        workspace_id: UUID | None = None,
    ) -> list[NotificationMessage]:
        due = [
            message
            for message in self.messages.values()
            if message.status == NotificationStatus.QUEUED.value
            and (workspace_id is None or message.workspace_id == workspace_id)
        ][:limit]
        for message in due:
            message.status = NotificationStatus.SENDING.value
            message.attempts = (message.attempts or 0) + 1
            message.locked_by = worker_id
            message.last_attempted_at = now
        return due

    async def update_message(self, message: NotificationMessage) -> NotificationMessage:
        self.ensure_message_fields(message)
        self.messages[message.id] = message
        return message

    async def create_event(self, event: NotificationEvent) -> NotificationEvent:
        self.ensure_event_fields(event)
        self.events[event.id] = event
        return event

    async def get_event(self, event_id: UUID) -> NotificationEvent | None:
        return self.events.get(event_id)

    async def get_recent_event_by_dedupe_key(
        self,
        workspace_id: UUID,
        dedupe_key: str,
        statuses: set[object],
        since: datetime,
    ) -> NotificationEvent | None:
        return None

    async def list_events(
        self,
        workspace_id: UUID,
        event_type: object | None = None,
        status: object | None = None,
        severity: str | None = None,
        source_type: str | None = None,
        inbox_status: object | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationEvent]:
        rows = [
            event
            for event in self.events.values()
            if event.workspace_id == workspace_id
            and (severity is None or event.severity == severity)
            and (source_type is None or event.source_type == source_type)
        ]
        return rows[offset : offset + limit]

    async def update_event(self, event: NotificationEvent) -> NotificationEvent:
        self.ensure_event_fields(event)
        self.events[event.id] = event
        return event

    async def create_worker_run(
        self,
        worker_id: str,
        workspace_id: UUID | None,
        batch_limit: int,
    ) -> NotificationWorkerRun:
        now = utc_now()
        run = NotificationWorkerRun(
            id=uuid4(),
            worker_id=worker_id,
            workspace_id=workspace_id,
            status="running",
            batch_limit=batch_limit,
            started_at=now,
            created_at=now,
        )
        self.worker_runs.append(run)
        return run

    async def update_worker_run(self, run: NotificationWorkerRun) -> NotificationWorkerRun:
        return run

    async def get_latest_worker_run(
        self,
        worker_id: str | None = None,
    ) -> NotificationWorkerRun | None:
        if not self.worker_runs:
            return None
        return self.worker_runs[-1]

    async def count_messages_by_status(
        self,
        status: NotificationStatus,
        workspace_id: UUID | None = None,
    ) -> int:
        return sum(
            1
            for message in self.messages.values()
            if message.status == status.value
            and (workspace_id is None or message.workspace_id == workspace_id)
        )

    async def oldest_due_at(self, workspace_id: UUID | None = None) -> datetime | None:
        due_at_values = [
            message.due_at
            for message in self.messages.values()
            if message.status == NotificationStatus.QUEUED.value
            and (workspace_id is None or message.workspace_id == workspace_id)
            and message.due_at is not None
        ]
        return min(due_at_values) if due_at_values else None

    def ensure_message_fields(self, message: NotificationMessage) -> None:
        now = utc_now()
        if getattr(message, "id", None) is None:
            message.id = uuid4()
        if getattr(message, "attempts", None) is None:
            message.attempts = 0
        if getattr(message, "created_at", None) is None:
            message.created_at = now
        if getattr(message, "updated_at", None) is None:
            message.updated_at = now

    def ensure_preference_fields(self, preference: NotificationPreference) -> None:
        now = utc_now()
        if getattr(preference, "id", None) is None:
            preference.id = uuid4()
        if getattr(preference, "created_at", None) is None:
            preference.created_at = now
        if getattr(preference, "updated_at", None) is None:
            preference.updated_at = now

    def ensure_event_fields(self, event: NotificationEvent) -> None:
        now = utc_now()
        if getattr(event, "id", None) is None:
            event.id = uuid4()
        if getattr(event, "created_at", None) is None:
            event.created_at = now
        if getattr(event, "updated_at", None) is None:
            event.updated_at = now


def make_service(repository: FakeNotificationRepository) -> NotificationService:
    return NotificationService(
        cast(Any, FakeSession()),
        settings=Settings(_env_file=None, app_env=AppEnvironment.TEST),
        repository=cast(NotificationRepository, repository),
    )


def notification_payload(
    workspace_id: UUID,
    user_id: UUID | None = None,
    channel: NotificationChannel = NotificationChannel.IN_APP,
) -> NotificationCreateRequest:
    return NotificationCreateRequest(
        workspace_id=workspace_id,
        user_id=user_id,
        channel=channel,
        event_type=NotificationEventType.HUMAN_REVIEW_REQUESTED,
        severity=NotificationSeverity.MEDIUM,
        source_type=NotificationSourceType.ACTION_ITEM,
        source_id=uuid4(),
        title="Human review requested",
        body="A stored reasoning action item is waiting for operator review.",
    )


@pytest.mark.asyncio
async def test_queue_notification_rejects_unsafe_content() -> None:
    service = make_service(FakeNotificationRepository())
    payload = NotificationCreateRequest(
        workspace_id=uuid4(),
        event_type=NotificationEventType.MANUAL_OPERATOR_NOTE,
        title="Buy now",
        body="This is a guaranteed outcome.",
    )

    with pytest.raises(AppError, match="Notification content"):
        await service.queue_notification(payload)


@pytest.mark.asyncio
async def test_queue_notification_is_idempotent() -> None:
    workspace_id = uuid4()
    repository = FakeNotificationRepository()
    service = make_service(repository)
    payload = notification_payload(workspace_id)

    first = await service.queue_notification(payload)
    second = await service.queue_notification(payload)

    assert first.id == second.id
    assert len(repository.messages) == 1


@pytest.mark.asyncio
async def test_user_preference_can_skip_notification() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    repository = FakeNotificationRepository()
    service = make_service(repository)
    await service.upsert_preference(
        NotificationPreferenceUpsert(
            workspace_id=workspace_id,
            user_id=user_id,
            channel=NotificationChannel.IN_APP,
            event_type=NotificationEventType.HUMAN_REVIEW_REQUESTED,
            is_enabled=False,
        )
    )

    message = await service.queue_notification(notification_payload(workspace_id, user_id))

    assert message.status == NotificationStatus.SKIPPED.value
    assert message.result_json == {"reason": "notification_preference_disabled"}


@pytest.mark.asyncio
async def test_dispatch_due_notifications_delivers_in_app_messages() -> None:
    workspace_id = uuid4()
    repository = FakeNotificationRepository()
    service = make_service(repository)
    message = await service.queue_notification(notification_payload(workspace_id))

    result = await service.dispatch_due_notifications(workspace_id=workspace_id, limit=10)

    assert result.claimed_count == 1
    assert result.delivered_count == 1
    assert result.messages[0].message.id == message.id
    assert repository.messages[message.id].status == NotificationStatus.DELIVERED.value


@pytest.mark.asyncio
async def test_dispatch_due_notifications_fails_unconfigured_external_channel() -> None:
    workspace_id = uuid4()
    repository = FakeNotificationRepository()
    service = make_service(repository)
    message = await service.queue_notification(
        notification_payload(workspace_id, channel=NotificationChannel.EMAIL)
    )

    result = await service.dispatch_due_notifications(workspace_id=workspace_id, limit=10)

    assert result.failed_count == 1
    assert repository.messages[message.id].status == NotificationStatus.FAILED.value
    assert repository.messages[message.id].error_code == "notification_channel_not_configured"


@pytest.mark.asyncio
async def test_notification_event_can_be_acknowledged_for_inbox_review() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    repository = FakeNotificationRepository()
    service = make_service(repository)
    event = await service.create_notification_event(
        NotificationEventCreate(
            workspace_id=workspace_id,
            event_type=BackendNotificationEventType.PROVIDER_HEALTH_DEGRADED,
            source_type="provider_health",
            source_id=uuid4(),
            severity=NotificationEventSeverity.MEDIUM,
            title="Provider degraded",
            summary="Review stored provider health context.",
            payload_json={"sourceType": "provider_health"},
        )
    )

    acknowledged = await service.acknowledge_notification_event(event.id, user_id=user_id)

    assert acknowledged.inbox_status == NotificationInboxStatus.ACKNOWLEDGED.value
    assert acknowledged.read_at is not None
    assert acknowledged.acknowledged_at is not None
    assert acknowledged.acknowledged_by_user_id == user_id
