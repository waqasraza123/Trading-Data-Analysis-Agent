import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.explanations.safety import check_explanation_safety
from app.modules.notifications.adapters import (
    DiscordNotificationAdapter,
    EmailNotificationAdapter,
    NotificationAdapter,
    NotificationAdapterRequest,
    NotificationAdapterResult,
    TelegramNotificationAdapter,
    WebhookNotificationAdapter,
)
from app.modules.notifications.dedupe import build_notification_dedupe_key
from app.modules.notifications.models import (
    BackendNotificationEventType,
    NotificationChannel,
    NotificationChannelStatus,
    NotificationDeliveryAttempt,
    NotificationDeliveryAttemptStatus,
    NotificationDeliveryChannel,
    NotificationDeliveryChannelType,
    NotificationEvent,
    NotificationEventSeverity,
    NotificationEventStatus,
    NotificationInboxStatus,
    NotificationMessage,
    NotificationPreference,
    NotificationSeverity,
    NotificationStatus,
    NotificationWorkerRunStatus,
)
from app.modules.notifications.quiet_hours import evaluate_quiet_hours
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.safety import (
    sanitize_notification_delivery_payload,
    should_redact_key,
)
from app.modules.notifications.schemas import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationCreateRequest,
    NotificationDeliveryAttemptRead,
    NotificationDeliveryResponse,
    NotificationDispatchResponse,
    NotificationDispatchResult,
    NotificationEventCreate,
    NotificationEventRead,
    NotificationPreferenceUpsert,
    NotificationRead,
    NotificationWorkerRunRead,
    NotificationWorkerStatusRead,
)
from app.modules.safety_policies.schemas import SafetyStatus

SEVERITY_RANK = {
    NotificationSeverity.INFO.value: 0,
    NotificationSeverity.LOW.value: 1,
    NotificationSeverity.MEDIUM.value: 2,
    NotificationSeverity.HIGH.value: 3,
}

EVENT_SEVERITY_RANK = {
    NotificationEventSeverity.INFO.value: 0,
    NotificationEventSeverity.LOW.value: 1,
    NotificationEventSeverity.MEDIUM.value: 2,
    NotificationEventSeverity.HIGH.value: 3,
    NotificationEventSeverity.CRITICAL.value: 4,
}

DEDUPED_EVENT_STATUSES = {
    NotificationEventStatus.DELIVERED,
    NotificationEventStatus.PARTIALLY_DELIVERED,
    NotificationEventStatus.HELD,
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
        adapters: dict[str, NotificationAdapter] | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or NotificationRepository(session)
        self.adapters = adapters or {
            NotificationDeliveryChannelType.WEBHOOK.value: WebhookNotificationAdapter(),
            NotificationDeliveryChannelType.EMAIL.value: EmailNotificationAdapter(),
            NotificationDeliveryChannelType.TELEGRAM.value: TelegramNotificationAdapter(),
            NotificationDeliveryChannelType.DISCORD.value: DiscordNotificationAdapter(),
        }

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

    async def create_channel(
        self,
        payload: NotificationChannelCreate,
    ) -> NotificationDeliveryChannel:
        self.validate_channel_config(payload.config_json)
        channel = NotificationDeliveryChannel(
            workspace_id=payload.workspace_id,
            name=payload.name.strip(),
            channel_type=payload.channel_type.value,
            status=payload.status.value,
            config_json=payload.config_json,
            secret_ref=payload.secret_ref.strip() if payload.secret_ref is not None else None,
            event_types_json=[event_type.value for event_type in payload.event_types_json],
            severity_filter_json=payload.severity_filter_json,
            quiet_hours_json=payload.quiet_hours_json,
            metadata_json=payload.metadata_json,
        )
        channel = await self.repository.create_channel(channel)
        await self.session.commit()
        return channel

    async def list_channels(
        self,
        workspace_id: UUID,
        status: NotificationChannelStatus | None = None,
        channel_type: NotificationDeliveryChannelType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationDeliveryChannel]:
        return await self.repository.list_channels(
            workspace_id=workspace_id,
            status=status,
            channel_type=channel_type.value if channel_type is not None else None,
            limit=limit,
            offset=offset,
        )

    async def get_channel(self, channel_id: UUID) -> NotificationDeliveryChannel:
        channel = await self.repository.get_channel(channel_id)
        if channel is None:
            raise AppError(404, "notification_channel_not_found", "Notification channel not found")
        return channel

    async def update_channel(
        self,
        channel_id: UUID,
        payload: NotificationChannelUpdate,
    ) -> NotificationDeliveryChannel:
        channel = await self.get_channel(channel_id)
        if channel.status == NotificationChannelStatus.ARCHIVED.value:
            raise AppError(
                409,
                "notification_channel_archived",
                "Archived notification channels cannot be updated",
            )
        if payload.name is not None:
            channel.name = payload.name.strip()
        if payload.status is not None:
            channel.status = payload.status.value
        if payload.config_json is not None:
            self.validate_channel_config(payload.config_json)
            channel.config_json = payload.config_json
        if payload.secret_ref is not None:
            channel.secret_ref = payload.secret_ref.strip()
        if payload.event_types_json is not None:
            channel.event_types_json = [event_type.value for event_type in payload.event_types_json]
        if payload.severity_filter_json is not None:
            channel.severity_filter_json = payload.severity_filter_json
        if payload.quiet_hours_json is not None:
            channel.quiet_hours_json = payload.quiet_hours_json
        if payload.metadata_json is not None:
            channel.metadata_json = payload.metadata_json
        channel = await self.repository.update_channel(channel)
        await self.session.commit()
        return channel

    async def archive_channel(self, channel_id: UUID) -> NotificationDeliveryChannel:
        channel = await self.get_channel(channel_id)
        channel.status = NotificationChannelStatus.ARCHIVED.value
        channel = await self.repository.update_channel(channel)
        await self.session.commit()
        return channel

    async def create_notification_event(
        self,
        payload: NotificationEventCreate,
    ) -> NotificationEvent:
        safety = sanitize_notification_delivery_payload(
            title=payload.title,
            summary=payload.summary,
            payload_json=payload.payload_json,
            max_payload_bytes=self.settings.notification_max_payload_bytes,
        )
        dedupe_key = payload.dedupe_key or build_notification_dedupe_key(
            workspace_id=payload.workspace_id,
            event_type=payload.event_type,
            source_type=payload.source_type,
            source_id=payload.source_id,
            severity=payload.severity,
        )
        if self.settings.notification_dedupe_window_seconds > 0:
            existing = await self.repository.get_recent_event_by_dedupe_key(
                workspace_id=payload.workspace_id,
                dedupe_key=dedupe_key,
                statuses=DEDUPED_EVENT_STATUSES,
                since=utc_now()
                - timedelta(seconds=self.settings.notification_dedupe_window_seconds),
            )
            if existing is not None:
                return existing
        status = (
            NotificationEventStatus.BLOCKED
            if safety.safety_status == SafetyStatus.BLOCKED
            else NotificationEventStatus.PENDING
        )
        event = NotificationEvent(
            workspace_id=payload.workspace_id,
            event_type=payload.event_type.value,
            source_type=payload.source_type.strip().lower(),
            source_id=payload.source_id,
            severity=payload.severity.value,
            status=status.value,
            title=safety.title,
            summary=safety.summary,
            payload_json=safety.payload_json
            | {
                "deliverySafety": {
                    "warnings": safety.warnings,
                    "blockedTerms": safety.blocked_terms,
                }
            },
            safety_status=safety.safety_status.value,
            dedupe_key=dedupe_key,
            inbox_status=NotificationInboxStatus.UNREAD.value,
        )
        event = await self.repository.create_event(event)
        await self.session.commit()
        return event

    async def route_notification_event(
        self,
        event_id: UUID,
    ) -> list[NotificationDeliveryChannel]:
        event = await self.get_notification_event(event_id)
        if event.status == NotificationEventStatus.BLOCKED.value:
            return []
        event_type = BackendNotificationEventType(event.event_type)
        channels = await self.repository.list_active_channels_for_event(
            workspace_id=event.workspace_id,
            event_type=event_type,
        )
        return [channel for channel in channels if self.channel_allows_severity(channel, event)]

    async def deliver_notification_event(self, event_id: UUID) -> NotificationDeliveryResponse:
        event = await self.get_notification_event(event_id)
        if not self.settings.notifications_enabled:
            raise AppError(
                409,
                "notifications_disabled",
                "Notification delivery is disabled by configuration",
            )
        if event.status == NotificationEventStatus.CANCELLED.value:
            raise AppError(409, "notification_event_cancelled", "Cancelled events cannot deliver")
        if event.status == NotificationEventStatus.BLOCKED.value:
            attempts = await self.repository.list_delivery_attempts(event.id)
            return self.delivery_response(event, attempts)
        channels = await self.route_notification_event(event.id)
        if not channels:
            event.status = NotificationEventStatus.HELD.value
            event = await self.repository.update_event(event)
            await self.session.commit()
            return self.delivery_response(event, [])
        attempts: list[NotificationDeliveryAttempt] = []
        now = utc_now()
        held_by_quiet_hours = False
        for channel in channels:
            quiet_hours = evaluate_quiet_hours(
                channel.quiet_hours_json,
                now,
                self.settings.notification_default_quiet_hours_timezone,
            )
            if quiet_hours.inside_quiet_hours:
                held_by_quiet_hours = held_by_quiet_hours or quiet_hours.behavior == "hold"
                attempts.append(
                    await self.record_delivery_attempt(
                        event=event,
                        channel=channel,
                        status=NotificationDeliveryAttemptStatus.SKIPPED,
                        attempted_at=now,
                        error_message="Delivery skipped by channel quiet hours",
                        metadata_json={
                            "reason": quiet_hours.reason,
                            "behavior": quiet_hours.behavior,
                        },
                    )
                )
                continue
            adapter = self.adapters.get(channel.channel_type)
            if adapter is None:
                attempts.append(
                    await self.record_delivery_attempt(
                        event=event,
                        channel=channel,
                        status=NotificationDeliveryAttemptStatus.SKIPPED,
                        attempted_at=now,
                        error_message="Notification adapter is not configured",
                        metadata_json={"reason": "adapter_not_configured"},
                    )
                )
                continue
            result = await adapter.deliver(
                NotificationAdapterRequest(
                    workspace_id=event.workspace_id,
                    event_id=event.id,
                    channel_id=channel.id,
                    event_type=event.event_type,
                    severity=event.severity,
                    title=event.title,
                    summary=event.summary,
                    payload_json=event.payload_json,
                    config_json=channel.config_json,
                    secret_ref=channel.secret_ref,
                    timeout_seconds=self.settings.notification_delivery_timeout_seconds,
                    user_agent=self.settings.notification_webhook_user_agent,
                )
            )
            attempts.append(
                await self.record_delivery_attempt(
                    event=event,
                    channel=channel,
                    status=self.attempt_status_from_adapter_result(result),
                    attempted_at=now,
                    response_status_code=result.response_status_code,
                    response_body_excerpt=result.response_body_excerpt,
                    error_message=result.error_message,
                    metadata_json=result.metadata_json,
                )
            )
        event.status = self.status_from_attempts(attempts, held_by_quiet_hours).value
        event = await self.repository.update_event(event)
        await self.session.commit()
        return self.delivery_response(event, attempts)

    async def list_notification_events(
        self,
        workspace_id: UUID,
        event_type: BackendNotificationEventType | None = None,
        status: NotificationEventStatus | None = None,
        severity: NotificationEventSeverity | None = None,
        source_type: str | None = None,
        inbox_status: NotificationInboxStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationEvent]:
        return await self.repository.list_events(
            workspace_id=workspace_id,
            event_type=event_type,
            status=status,
            severity=severity.value if severity is not None else None,
            source_type=source_type.strip().lower() if source_type else None,
            inbox_status=inbox_status,
            limit=limit,
            offset=offset,
        )

    async def get_notification_event(self, event_id: UUID) -> NotificationEvent:
        event = await self.repository.get_event(event_id)
        if event is None:
            raise AppError(404, "notification_event_not_found", "Notification event not found")
        return event

    async def mark_notification_event_read(self, event_id: UUID) -> NotificationEvent:
        event = await self.get_notification_event(event_id)
        if event.read_at is None:
            event.read_at = utc_now()
        if event.inbox_status == NotificationInboxStatus.UNREAD.value:
            event.inbox_status = NotificationInboxStatus.READ.value
        event = await self.repository.update_event(event)
        await self.session.commit()
        return event

    async def acknowledge_notification_event(
        self,
        event_id: UUID,
        user_id: UUID | None = None,
    ) -> NotificationEvent:
        event = await self.get_notification_event(event_id)
        now = utc_now()
        if event.read_at is None:
            event.read_at = now
        if event.acknowledged_at is None:
            event.acknowledged_at = now
        if user_id is not None:
            event.acknowledged_by_user_id = user_id
        event.inbox_status = NotificationInboxStatus.ACKNOWLEDGED.value
        event = await self.repository.update_event(event)
        await self.session.commit()
        return event

    async def archive_notification_event(self, event_id: UUID) -> NotificationEvent:
        event = await self.get_notification_event(event_id)
        event.inbox_status = NotificationInboxStatus.ARCHIVED.value
        event = await self.repository.update_event(event)
        await self.session.commit()
        return event

    async def list_delivery_attempts(
        self,
        event_id: UUID,
    ) -> list[NotificationDeliveryAttempt]:
        await self.get_notification_event(event_id)
        return await self.repository.list_delivery_attempts(event_id)

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

    async def record_delivery_attempt(
        self,
        event: NotificationEvent,
        channel: NotificationDeliveryChannel,
        status: NotificationDeliveryAttemptStatus,
        attempted_at: datetime,
        response_status_code: int | None = None,
        response_body_excerpt: str | None = None,
        error_message: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> NotificationDeliveryAttempt:
        attempt = NotificationDeliveryAttempt(
            workspace_id=event.workspace_id,
            notification_event_id=event.id,
            channel_id=channel.id,
            status=status.value,
            attempted_at=attempted_at,
            response_status_code=response_status_code,
            response_body_excerpt=(
                response_body_excerpt[:1000] if response_body_excerpt is not None else None
            ),
            error_message=error_message,
            metadata_json=metadata_json or {},
        )
        return await self.repository.create_delivery_attempt(attempt)

    def attempt_status_from_adapter_result(
        self,
        result: NotificationAdapterResult,
    ) -> NotificationDeliveryAttemptStatus:
        if result.blocked:
            return NotificationDeliveryAttemptStatus.BLOCKED
        if result.delivered:
            return NotificationDeliveryAttemptStatus.DELIVERED
        if result.skipped:
            return NotificationDeliveryAttemptStatus.SKIPPED
        return NotificationDeliveryAttemptStatus.FAILED

    def status_from_attempts(
        self,
        attempts: list[NotificationDeliveryAttempt],
        held_by_quiet_hours: bool,
    ) -> NotificationEventStatus:
        if not attempts:
            return NotificationEventStatus.HELD
        delivered_count = sum(
            1
            for attempt in attempts
            if attempt.status == NotificationDeliveryAttemptStatus.DELIVERED.value
        )
        blocked_count = sum(
            1
            for attempt in attempts
            if attempt.status == NotificationDeliveryAttemptStatus.BLOCKED.value
        )
        failed_count = sum(
            1
            for attempt in attempts
            if attempt.status == NotificationDeliveryAttemptStatus.FAILED.value
        )
        skipped_count = sum(
            1
            for attempt in attempts
            if attempt.status == NotificationDeliveryAttemptStatus.SKIPPED.value
        )
        if delivered_count == len(attempts):
            return NotificationEventStatus.DELIVERED
        if delivered_count:
            return NotificationEventStatus.PARTIALLY_DELIVERED
        if blocked_count:
            return NotificationEventStatus.BLOCKED
        if failed_count:
            return NotificationEventStatus.FAILED
        if skipped_count or held_by_quiet_hours:
            return NotificationEventStatus.HELD
        return NotificationEventStatus.FAILED

    def channel_allows_severity(
        self,
        channel: NotificationDeliveryChannel,
        event: NotificationEvent,
    ) -> bool:
        severity_filter = channel.severity_filter_json or {}
        severities = severity_filter.get("severities")
        if isinstance(severities, list) and severities:
            return event.severity in {str(severity).lower() for severity in severities}
        minimum = severity_filter.get("min_severity") or severity_filter.get("minSeverity")
        if isinstance(minimum, str) and minimum.lower() in EVENT_SEVERITY_RANK:
            return EVENT_SEVERITY_RANK[event.severity] >= EVENT_SEVERITY_RANK[minimum.lower()]
        return True

    def delivery_response(
        self,
        event: NotificationEvent,
        attempts: list[NotificationDeliveryAttempt],
    ) -> NotificationDeliveryResponse:
        return NotificationDeliveryResponse(
            event=NotificationEventRead.model_validate(event),
            attempts=[
                NotificationDeliveryAttemptRead.model_validate(attempt) for attempt in attempts
            ],
        )

    def validate_channel_config(self, config_json: dict[str, object]) -> None:
        unsafe_keys = sorted(find_secret_config_keys(config_json))
        if unsafe_keys:
            raise AppError(
                422,
                "notification_channel_config_contains_secret",
                "Notification channel config must not contain inline secrets; use secret_ref",
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


def find_secret_config_keys(value: object, path: str = "$") -> set[str]:
    if isinstance(value, dict):
        matches: set[str] = set()
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            next_path = f"{path}.{key}"
            if should_redact_key(key.lower()):
                matches.add(next_path)
            matches.update(find_secret_config_keys(raw_value, next_path))
        return matches
    if isinstance(value, list):
        matches: set[str] = set()
        for index, item in enumerate(value):
            matches.update(find_secret_config_keys(item, f"{path}[{index}]"))
        return matches
    return set()
