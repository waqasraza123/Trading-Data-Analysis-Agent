from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.modules.notifications.models import (
    BackendNotificationEventType,
    NotificationChannelStatus,
    NotificationDeliveryAttempt,
    NotificationDeliveryChannel,
    NotificationEvent,
    NotificationEventStatus,
    NotificationInboxStatus,
    NotificationMessage,
    NotificationPreference,
    NotificationStatus,
    NotificationWorkerRun,
    NotificationWorkerRunStatus,
)


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_preference(
        self,
        preference: NotificationPreference,
    ) -> NotificationPreference:
        existing = await self.get_preference(
            workspace_id=preference.workspace_id,
            user_id=preference.user_id,
            channel=preference.channel,
            event_type=preference.event_type,
        )
        if existing is None:
            self.session.add(preference)
            await self.session.flush()
            await self.session.refresh(preference)
            return preference
        existing.is_enabled = preference.is_enabled
        existing.min_severity = preference.min_severity
        existing.destination_json = preference.destination_json
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def get_preference(
        self,
        workspace_id: UUID,
        user_id: UUID,
        channel: str,
        event_type: str,
    ) -> NotificationPreference | None:
        statement: Select[tuple[NotificationPreference]] = select(NotificationPreference).where(
            NotificationPreference.workspace_id == workspace_id,
            NotificationPreference.user_id == user_id,
            NotificationPreference.channel == channel,
            NotificationPreference.event_type == event_type,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_preferences(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
    ) -> list[NotificationPreference]:
        statement: Select[tuple[NotificationPreference]] = (
            select(NotificationPreference)
            .where(NotificationPreference.workspace_id == workspace_id)
            .order_by(NotificationPreference.user_id.asc(), NotificationPreference.event_type.asc())
        )
        if user_id is not None:
            statement = statement.where(NotificationPreference.user_id == user_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_message(self, message: NotificationMessage) -> NotificationMessage:
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def get_message(self, message_id: UUID) -> NotificationMessage | None:
        return await self.session.get(NotificationMessage, message_id)

    async def get_message_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str,
    ) -> NotificationMessage | None:
        statement: Select[tuple[NotificationMessage]] = select(NotificationMessage).where(
            NotificationMessage.workspace_id == workspace_id,
            NotificationMessage.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_messages(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
        status: NotificationStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationMessage]:
        statement: Select[tuple[NotificationMessage]] = (
            select(NotificationMessage)
            .where(NotificationMessage.workspace_id == workspace_id)
            .order_by(NotificationMessage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if user_id is not None:
            statement = statement.where(NotificationMessage.user_id == user_id)
        if status is not None:
            statement = statement.where(NotificationMessage.status == status.value)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def claim_due_messages(
        self,
        now: datetime,
        worker_id: str,
        limit: int,
        lock_seconds: int,
        max_attempts: int,
        workspace_id: UUID | None = None,
    ) -> list[NotificationMessage]:
        lock_until = now + timedelta(seconds=lock_seconds)
        statement: Select[tuple[NotificationMessage]] = (
            select(NotificationMessage)
            .where(
                NotificationMessage.attempts < NotificationMessage.max_attempts,
                NotificationMessage.attempts < max_attempts,
                or_(NotificationMessage.due_at.is_(None), NotificationMessage.due_at <= now),
                or_(
                    and_(
                        NotificationMessage.status == NotificationStatus.QUEUED.value,
                        or_(
                            NotificationMessage.locked_by.is_(None),
                            NotificationMessage.locked_until.is_(None),
                            NotificationMessage.locked_until <= now,
                        ),
                    ),
                    and_(
                        NotificationMessage.status == NotificationStatus.SENDING.value,
                        NotificationMessage.locked_until.is_not(None),
                        NotificationMessage.locked_until <= now,
                    ),
                ),
            )
            .order_by(NotificationMessage.due_at.asc().nullsfirst(), NotificationMessage.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        if workspace_id is not None:
            statement = statement.where(NotificationMessage.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        messages = list(result.scalars().all())
        for message in messages:
            message.status = NotificationStatus.SENDING.value
            message.attempts += 1
            message.last_attempted_at = now
            message.locked_by = worker_id
            message.locked_until = lock_until
            message.error_code = None
            message.error_message = None
        await self.session.flush()
        return messages

    async def update_message(self, message: NotificationMessage) -> NotificationMessage:
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def create_worker_run(
        self,
        worker_id: str,
        workspace_id: UUID | None,
        batch_limit: int,
    ) -> NotificationWorkerRun:
        run = NotificationWorkerRun(
            worker_id=worker_id,
            workspace_id=workspace_id,
            status=NotificationWorkerRunStatus.RUNNING.value,
            batch_limit=batch_limit,
            started_at=utc_now(),
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_worker_run(self, run: NotificationWorkerRun) -> NotificationWorkerRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_latest_worker_run(
        self,
        worker_id: str | None = None,
    ) -> NotificationWorkerRun | None:
        statement: Select[tuple[NotificationWorkerRun]] = (
            select(NotificationWorkerRun).order_by(NotificationWorkerRun.started_at.desc()).limit(1)
        )
        if worker_id is not None:
            statement = statement.where(NotificationWorkerRun.worker_id == worker_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def count_messages_by_status(
        self,
        status: NotificationStatus,
        workspace_id: UUID | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(NotificationMessage)
            .where(NotificationMessage.status == status.value)
        )
        if workspace_id is not None:
            statement = statement.where(NotificationMessage.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one() or 0)

    async def oldest_due_at(self, workspace_id: UUID | None = None) -> datetime | None:
        statement = select(func.min(NotificationMessage.due_at)).where(
            NotificationMessage.status == NotificationStatus.QUEUED.value
        )
        if workspace_id is not None:
            statement = statement.where(NotificationMessage.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_channel(
        self,
        channel: NotificationDeliveryChannel,
    ) -> NotificationDeliveryChannel:
        self.session.add(channel)
        await self.session.flush()
        await self.session.refresh(channel)
        return channel

    async def get_channel(self, channel_id: UUID) -> NotificationDeliveryChannel | None:
        return await self.session.get(NotificationDeliveryChannel, channel_id)

    async def list_channels(
        self,
        workspace_id: UUID,
        status: NotificationChannelStatus | None = None,
        channel_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationDeliveryChannel]:
        statement: Select[tuple[NotificationDeliveryChannel]] = (
            select(NotificationDeliveryChannel)
            .where(NotificationDeliveryChannel.workspace_id == workspace_id)
            .order_by(NotificationDeliveryChannel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(NotificationDeliveryChannel.status == status.value)
        if channel_type is not None:
            statement = statement.where(NotificationDeliveryChannel.channel_type == channel_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_active_channels_for_event(
        self,
        workspace_id: UUID,
        event_type: BackendNotificationEventType,
    ) -> list[NotificationDeliveryChannel]:
        statement: Select[tuple[NotificationDeliveryChannel]] = (
            select(NotificationDeliveryChannel)
            .where(
                NotificationDeliveryChannel.workspace_id == workspace_id,
                NotificationDeliveryChannel.status == NotificationChannelStatus.ACTIVE.value,
            )
            .order_by(NotificationDeliveryChannel.created_at.asc())
        )
        result = await self.session.execute(statement)
        channels = list(result.scalars().all())
        return [
            channel
            for channel in channels
            if not channel.event_types_json or event_type.value in channel.event_types_json
        ]

    async def update_channel(
        self,
        channel: NotificationDeliveryChannel,
    ) -> NotificationDeliveryChannel:
        await self.session.flush()
        await self.session.refresh(channel)
        return channel

    async def create_event(self, event: NotificationEvent) -> NotificationEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get_event(self, event_id: UUID) -> NotificationEvent | None:
        return await self.session.get(NotificationEvent, event_id)

    async def get_recent_event_by_dedupe_key(
        self,
        workspace_id: UUID,
        dedupe_key: str,
        statuses: set[NotificationEventStatus],
        since: datetime,
    ) -> NotificationEvent | None:
        statement: Select[tuple[NotificationEvent]] = (
            select(NotificationEvent)
            .where(
                NotificationEvent.workspace_id == workspace_id,
                NotificationEvent.dedupe_key == dedupe_key,
                NotificationEvent.status.in_([status.value for status in statuses]),
                NotificationEvent.created_at >= since,
            )
            .order_by(NotificationEvent.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_events(
        self,
        workspace_id: UUID,
        event_type: BackendNotificationEventType | None = None,
        status: NotificationEventStatus | None = None,
        severity: str | None = None,
        source_type: str | None = None,
        inbox_status: NotificationInboxStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationEvent]:
        statement: Select[tuple[NotificationEvent]] = (
            select(NotificationEvent)
            .where(NotificationEvent.workspace_id == workspace_id)
            .order_by(NotificationEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if event_type is not None:
            statement = statement.where(NotificationEvent.event_type == event_type.value)
        if status is not None:
            statement = statement.where(NotificationEvent.status == status.value)
        if severity is not None:
            statement = statement.where(NotificationEvent.severity == severity)
        if source_type is not None:
            statement = statement.where(NotificationEvent.source_type == source_type)
        if inbox_status is not None:
            statement = statement.where(NotificationEvent.inbox_status == inbox_status.value)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_event(self, event: NotificationEvent) -> NotificationEvent:
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def create_delivery_attempt(
        self,
        attempt: NotificationDeliveryAttempt,
    ) -> NotificationDeliveryAttempt:
        self.session.add(attempt)
        await self.session.flush()
        await self.session.refresh(attempt)
        return attempt

    async def list_delivery_attempts(
        self,
        event_id: UUID,
    ) -> list[NotificationDeliveryAttempt]:
        statement: Select[tuple[NotificationDeliveryAttempt]] = (
            select(NotificationDeliveryAttempt)
            .where(NotificationDeliveryAttempt.notification_event_id == event_id)
            .order_by(NotificationDeliveryAttempt.attempted_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
