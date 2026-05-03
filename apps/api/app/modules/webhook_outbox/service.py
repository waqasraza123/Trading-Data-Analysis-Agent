from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.webhook_outbox.models import (
    WebhookEventType,
    WebhookOutboxEvent,
    WebhookOutboxEventStatus,
    WebhookSubscription,
    WebhookSubscriptionStatus,
)
from app.modules.webhook_outbox.payloads import WebhookPayloadBuilder
from app.modules.webhook_outbox.repository import WebhookOutboxRepository
from app.modules.webhook_outbox.schemas import (
    WebhookOutboxEventCreate,
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
)


class WebhookOutboxService:
    def __init__(
        self,
        session: AsyncSession,
        repository: WebhookOutboxRepository | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or WebhookOutboxRepository(session)
        self.payload_builder = WebhookPayloadBuilder(self.repository)

    async def create_subscription(
        self,
        payload: WebhookSubscriptionCreate,
    ) -> WebhookSubscription:
        subscription = WebhookSubscription(
            workspace_id=payload.workspace_id,
            name=payload.name.strip(),
            status=payload.status.value,
            target_url=payload.target_url,
            event_types_json=[event_type.value for event_type in payload.event_types_json],
            signing_secret_ref=payload.signing_secret_ref.strip()
            if payload.signing_secret_ref is not None
            else None,
            metadata_json=payload.metadata_json,
        )
        subscription = await self.repository.create_subscription(subscription)
        await self.session.commit()
        return subscription

    async def list_subscriptions(
        self,
        workspace_id: UUID,
        status: WebhookSubscriptionStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookSubscription]:
        return await self.repository.list_subscriptions(
            workspace_id=workspace_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def get_subscription(self, subscription_id: UUID) -> WebhookSubscription:
        subscription = await self.repository.get_subscription(subscription_id)
        if subscription is None:
            raise AppError(404, "webhook_subscription_not_found", "Webhook subscription not found")
        return subscription

    async def update_subscription(
        self,
        subscription_id: UUID,
        payload: WebhookSubscriptionUpdate,
    ) -> WebhookSubscription:
        subscription = await self.get_subscription(subscription_id)
        if subscription.status == WebhookSubscriptionStatus.ARCHIVED.value:
            raise AppError(
                409,
                "webhook_subscription_archived",
                "Archived webhook subscriptions cannot be updated",
            )
        if payload.name is not None:
            subscription.name = payload.name.strip()
        if payload.status is not None:
            subscription.status = payload.status.value
        if payload.target_url is not None:
            subscription.target_url = payload.target_url
        if payload.event_types_json is not None:
            subscription.event_types_json = [
                event_type.value for event_type in payload.event_types_json
            ]
        if payload.signing_secret_ref is not None:
            subscription.signing_secret_ref = payload.signing_secret_ref.strip()
        if payload.metadata_json is not None:
            subscription.metadata_json = payload.metadata_json
        subscription = await self.repository.update_subscription(subscription)
        await self.session.commit()
        return subscription

    async def archive_subscription(self, subscription_id: UUID) -> WebhookSubscription:
        subscription = await self.get_subscription(subscription_id)
        subscription.status = WebhookSubscriptionStatus.ARCHIVED.value
        subscription = await self.repository.update_subscription(subscription)
        await self.session.commit()
        return subscription

    async def build_outbox_event(
        self,
        payload: WebhookOutboxEventCreate,
    ) -> WebhookOutboxEvent:
        if payload.status not in {
            WebhookOutboxEventStatus.HELD,
            WebhookOutboxEventStatus.PENDING,
        }:
            raise AppError(
                422,
                "webhook_outbox_initial_status_not_allowed",
                "Outbox events can only be created as held or pending",
            )
        subscription = None
        if payload.subscription_id is not None:
            subscription = await self.get_subscription(payload.subscription_id)
            if subscription.workspace_id != payload.workspace_id:
                raise AppError(
                    422,
                    "webhook_subscription_workspace_mismatch",
                    "Webhook subscription does not belong to the requested workspace",
                )
            if subscription.status == WebhookSubscriptionStatus.ARCHIVED.value:
                raise AppError(
                    409,
                    "webhook_subscription_archived",
                    "Archived webhook subscriptions cannot receive outbox records",
                )
            if payload.event_type.value not in subscription.event_types_json:
                raise AppError(
                    422,
                    "webhook_subscription_event_type_not_enabled",
                    "Webhook subscription is not configured for this event type",
                )
        payload_json, redaction_warnings = await self.payload_builder.build_payload(
            workspace_id=payload.workspace_id,
            event_type=payload.event_type,
            source_type=payload.source_type,
            source_id=payload.source_id,
        )
        event = WebhookOutboxEvent(
            workspace_id=payload.workspace_id,
            subscription_id=subscription.id if subscription is not None else None,
            event_type=payload.event_type.value,
            source_type=payload.source_type,
            source_id=payload.source_id,
            status=payload.status.value,
            payload_json=payload_json,
            redaction_warnings_json=redaction_warnings,
            delivery_attempt_count=0,
        )
        event = await self.repository.create_outbox_event(event)
        await self.session.commit()
        return event

    async def list_outbox_events(
        self,
        workspace_id: UUID,
        event_type: WebhookEventType | None = None,
        status: WebhookOutboxEventStatus | None = None,
        source_type: str | None = None,
        source_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookOutboxEvent]:
        return await self.repository.list_outbox_events(
            workspace_id=workspace_id,
            event_type=event_type,
            status=status,
            source_type=source_type,
            source_id=source_id,
            limit=limit,
            offset=offset,
        )

    async def get_outbox_event(self, event_id: UUID) -> WebhookOutboxEvent:
        event = await self.repository.get_outbox_event(event_id)
        if event is None:
            raise AppError(404, "webhook_outbox_event_not_found", "Webhook outbox event not found")
        return event

    async def cancel_outbox_event(self, event_id: UUID) -> WebhookOutboxEvent:
        event = await self.get_outbox_event(event_id)
        if event.status not in {
            WebhookOutboxEventStatus.HELD.value,
            WebhookOutboxEventStatus.PENDING.value,
        }:
            raise AppError(
                409,
                "webhook_outbox_event_not_cancellable",
                "Only held or pending webhook outbox events can be cancelled",
            )
        event.status = WebhookOutboxEventStatus.CANCELLED.value
        event = await self.repository.update_outbox_event(event)
        await self.session.commit()
        return event
