import hashlib
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.explanations.safety import check_explanation_safety
from app.modules.notifications.models import (
    NotificationChannel,
    NotificationMessage,
    NotificationPreference,
    NotificationSeverity,
    NotificationStatus,
    NotificationWorkerRunStatus,
)
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import (
    NotificationCreateRequest,
    NotificationDispatchResponse,
    NotificationDispatchResult,
    NotificationPreferenceUpsert,
    NotificationRead,
    NotificationWorkerRunRead,
    NotificationWorkerStatusRead,
)

SEVERITY_RANK = {
    NotificationSeverity.INFO.value: 0,
    NotificationSeverity.LOW.value: 1,
    NotificationSeverity.MEDIUM.value: 2,
    NotificationSeverity.HIGH.value: 3,
}


@dataclass(frozen=True)
class NotificationDeliveryResult:
    message: NotificationMessage
    delivered: bool
    skipped: bool
    failed: bool


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: NotificationRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or NotificationRepository(session)

    async def upsert_preference(
        self,
        payload: NotificationPreferenceUpsert,
    ) -> NotificationPreference:
        preference = NotificationPreference(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            channel=payload.channel.value,
            event_type=payload.event_type.value,
            is_enabled=payload.is_enabled,
            min_severity=payload.min_severity.value,
            destination_json=payload.destination_json,
        )
        preference = await self.repository.upsert_preference(preference)
        await self.session.commit()
        return preference

    async def list_preferences(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
    ) -> list[NotificationPreference]:
        return await self.repository.list_preferences(workspace_id=workspace_id, user_id=user_id)

    async def queue_notification(self, payload: NotificationCreateRequest) -> NotificationMessage:
        blocked_terms = self.validate_notification_content(payload.title, payload.body)
        idempotency_key = payload.idempotency_key or self.build_idempotency_key(payload)
        existing = await self.repository.get_message_by_idempotency_key(
            payload.workspace_id,
            idempotency_key,
        )
        if existing is not None:
            return existing
        status = await self.resolve_initial_status(payload)
        message = NotificationMessage(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            channel=payload.channel.value,
            event_type=payload.event_type.value,
            severity=payload.severity.value,
            status=status.value,
            source_type=payload.source_type.value,
            source_id=payload.source_id,
            title=payload.title.strip(),
            body=payload.body.strip(),
            payload_json=payload.payload_json,
            idempotency_key=idempotency_key,
            blocked_terms_json=blocked_terms,
            max_attempts=payload.max_attempts,
            due_at=payload.due_at,
        )
        if status == NotificationStatus.SKIPPED:
            message.result_json = {"reason": "notification_preference_disabled"}
        message = await self.repository.create_message(message)
        await self.session.commit()
        return message

    async def list_notifications(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
        status: NotificationStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationMessage]:
        return await self.repository.list_messages(
            workspace_id=workspace_id,
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def get_notification(self, message_id: UUID) -> NotificationMessage:
        message = await self.repository.get_message(message_id)
        if message is None:
            raise AppError(404, "notification_not_found", "Notification not found")
        return message

    async def mark_read(self, message_id: UUID) -> NotificationMessage:
        message = await self.get_notification(message_id)
        if message.read_at is None:
            message.read_at = utc_now()
            await self.repository.update_message(message)
            await self.session.commit()
        return message

    async def dispatch_due_notifications(
        self,
        workspace_id: UUID | None = None,
        limit: int | None = None,
        worker_id: str = "api-request",
    ) -> NotificationDispatchResponse:
        batch_limit = limit or self.settings.notification_worker_batch_size
        run = await self.repository.create_worker_run(
            worker_id=worker_id,
            workspace_id=workspace_id,
            batch_limit=batch_limit,
        )
        claimed = await self.repository.claim_due_messages(
            now=utc_now(),
            worker_id=worker_id,
            workspace_id=workspace_id,
            limit=batch_limit,
            lock_seconds=self.settings.notification_worker_lock_seconds,
            max_attempts=self.settings.notification_worker_max_attempts,
        )
        run.claimed_count = len(claimed)
        run.metadata_json = {"notificationMessageIds": [str(message.id) for message in claimed]}
        results = [await self.dispatch_message(message) for message in claimed]
        run.delivered_count = sum(1 for result in results if result.delivered)
        run.skipped_count = sum(1 for result in results if result.skipped)
        run.failed_count = sum(1 for result in results if result.failed)
        run.completed_at = utc_now()
        if run.failed_count and (run.delivered_count or run.skipped_count):
            run.status = NotificationWorkerRunStatus.COMPLETED_WITH_WARNINGS.value
        elif run.failed_count:
            run.status = NotificationWorkerRunStatus.FAILED.value
        else:
            run.status = NotificationWorkerRunStatus.COMPLETED.value
        await self.repository.update_worker_run(run)
        await self.session.commit()
        return NotificationDispatchResponse(
            claimed_count=run.claimed_count,
            delivered_count=run.delivered_count,
            skipped_count=run.skipped_count,
            failed_count=run.failed_count,
            messages=[
                NotificationDispatchResult(
                    message=NotificationRead.model_validate(result.message),
                    delivered=result.delivered,
                    skipped=result.skipped,
                    failed=result.failed,
                )
                for result in results
            ],
        )

    async def worker_status(self, workspace_id: UUID | None = None) -> NotificationWorkerStatusRead:
        last_run = await self.repository.get_latest_worker_run()
        return NotificationWorkerStatusRead(
            queued_count=await self.repository.count_messages_by_status(
                NotificationStatus.QUEUED,
                workspace_id=workspace_id,
            ),
            sending_count=await self.repository.count_messages_by_status(
                NotificationStatus.SENDING,
                workspace_id=workspace_id,
            ),
            delivered_count=await self.repository.count_messages_by_status(
                NotificationStatus.DELIVERED,
                workspace_id=workspace_id,
            ),
            failed_count=await self.repository.count_messages_by_status(
                NotificationStatus.FAILED,
                workspace_id=workspace_id,
            ),
            oldest_due_at=await self.repository.oldest_due_at(workspace_id=workspace_id),
            worker_enabled=self.settings.notification_worker_enabled,
            last_worker_run=(
                NotificationWorkerRunRead.model_validate(last_run) if last_run is not None else None
            ),
        )

    async def dispatch_message(self, message: NotificationMessage) -> NotificationDeliveryResult:
        now = utc_now()
        message.locked_by = None
        message.locked_until = None
        if message.status == NotificationStatus.SKIPPED.value:
            await self.repository.update_message(message)
            return NotificationDeliveryResult(
                message=message,
                delivered=False,
                skipped=True,
                failed=False,
            )
        if message.channel == NotificationChannel.IN_APP.value:
            message.status = NotificationStatus.DELIVERED.value
            message.delivered_at = now
            message.result_json = {"delivery": "stored_in_app"}
            await self.repository.update_message(message)
            return NotificationDeliveryResult(
                message=message,
                delivered=True,
                skipped=False,
                failed=False,
            )
        message.status = NotificationStatus.FAILED.value
        message.error_code = "notification_channel_not_configured"
        message.error_message = "Only in-app notification delivery is currently configured"
        await self.repository.update_message(message)
        return NotificationDeliveryResult(
            message=message,
            delivered=False,
            skipped=False,
            failed=True,
        )

    async def resolve_initial_status(
        self,
        payload: NotificationCreateRequest,
    ) -> NotificationStatus:
        if payload.user_id is None:
            return NotificationStatus.QUEUED
        preference = await self.repository.get_preference(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            channel=payload.channel.value,
            event_type=payload.event_type.value,
        )
        if preference is None:
            return NotificationStatus.QUEUED
        if not preference.is_enabled:
            return NotificationStatus.SKIPPED
        if SEVERITY_RANK[payload.severity.value] < SEVERITY_RANK[preference.min_severity]:
            return NotificationStatus.SKIPPED
        return NotificationStatus.QUEUED

    def validate_notification_content(self, title: str, body: str) -> list[str]:
        safety = check_explanation_safety(f"{title}\n{body}")
        if not safety.passed:
            raise AppError(
                422,
                "unsafe_notification_content",
                "Notification content includes blocked trading or guarantee language",
            )
        return safety.blocked_terms

    def build_idempotency_key(self, payload: NotificationCreateRequest) -> str:
        source_id = str(payload.source_id) if payload.source_id is not None else "none"
        user_id = str(payload.user_id) if payload.user_id is not None else "workspace"
        digest = hashlib.sha256(
            "|".join(
                [
                    str(payload.workspace_id),
                    user_id,
                    payload.channel.value,
                    payload.event_type.value,
                    payload.source_type.value,
                    source_id,
                    payload.title.strip(),
                ]
            ).encode("utf-8")
        ).hexdigest()[:32]
        return f"notification:{digest}"
