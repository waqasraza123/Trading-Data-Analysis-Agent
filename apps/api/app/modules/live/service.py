import logging
from datetime import datetime, timedelta
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.candles.normalizer import normalize_candle_payload
from app.modules.candles.repository import CandleRepository
from app.modules.candles.schemas import (
    CandleOriginType,
    CandleUpsertStatus,
    NormalizedCandleInput,
)
from app.modules.candles.timeframes import Timeframe
from app.modules.candles.validator import validate_candle
from app.modules.data_sources.models import DataSource, DataSourceStatus, DataSourceType
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.live.heartbeat import LiveStalePolicy, subscription_is_stale
from app.modules.live.models import (
    LiveFeedEvent,
    LiveFeedEventProcessingStatus,
    LiveFeedEventType,
    LiveFeedSubscription,
    LiveFeedSubscriptionStatus,
)
from app.modules.live.providers.registry import get_live_provider
from app.modules.live.repository import LiveRepository
from app.modules.live.schemas import (
    LiveProviderMessage,
    LiveSubscriptionCreate,
    LiveSubscriptionUpdate,
    NormalizedLiveProviderEvent,
)
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository

logger = logging.getLogger(__name__)


class LiveService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = LiveRepository(session)
        self.candle_repository = CandleRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def create_subscription(
        self,
        payload: LiveSubscriptionCreate,
    ) -> LiveFeedSubscription:
        get_live_provider(payload.provider)
        await self.validate_symbol_and_source(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
        )
        subscription = LiveFeedSubscription(
            workspace_id=payload.workspace_id,
            source_id=payload.source_id,
            symbol_id=payload.symbol_id,
            timeframe=payload.timeframe.value,
            provider=payload.provider,
            status=LiveFeedSubscriptionStatus.ACTIVE,
            config_json=payload.config_json,
        )
        try:
            created_subscription = await self.repository.create_subscription(subscription)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "live_subscription_conflict",
                "Live subscription could not be created",
            ) from error
        return created_subscription

    async def list_subscriptions(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        status: str | None = None,
        provider: str | None = None,
        symbol_id: UUID | None = None,
    ) -> list[LiveFeedSubscription]:
        return await self.repository.list_subscriptions(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            status=status,
            provider=provider,
            symbol_id=symbol_id,
        )

    async def get_subscription(self, subscription_id: UUID) -> LiveFeedSubscription:
        subscription = await self.repository.get_subscription(subscription_id)
        if subscription is None:
            raise AppError(404, "live_subscription_not_found", "Live subscription not found")
        return subscription

    async def update_subscription(
        self,
        subscription_id: UUID,
        payload: LiveSubscriptionUpdate,
    ) -> LiveFeedSubscription:
        subscription = await self.get_subscription(subscription_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        if "provider" in updates:
            get_live_provider(updates["provider"])
        source_id = updates.get("source_id", subscription.source_id)
        symbol_id = updates.get("symbol_id", subscription.symbol_id)
        await self.validate_symbol_and_source(
            workspace_id=subscription.workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
        )
        if "timeframe" in updates:
            updates["timeframe"] = updates["timeframe"].value
        for field_name, field_value in updates.items():
            setattr(subscription, field_name, field_value)
        try:
            await self.session.flush()
            await self.session.refresh(subscription)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "live_subscription_conflict",
                "Live subscription could not be updated",
            ) from error
        return subscription

    async def set_subscription_status(
        self,
        subscription_id: UUID,
        status: LiveFeedSubscriptionStatus,
    ) -> LiveFeedSubscription:
        subscription = await self.get_subscription(subscription_id)
        subscription.status = status
        if status == LiveFeedSubscriptionStatus.ACTIVE:
            subscription.last_error = None
        if status in {
            LiveFeedSubscriptionStatus.PAUSED,
            LiveFeedSubscriptionStatus.FAILED,
            LiveFeedSubscriptionStatus.STOPPED,
        }:
            subscription.worker_id = None
            subscription.lease_expires_at = None
        await self.session.flush()
        await self.session.refresh(subscription)
        await self.session.commit()
        return subscription

    async def start_subscription_runtime(self, subscription_id: UUID) -> LiveFeedSubscription:
        subscription = await self.set_subscription_status(
            subscription_id,
            LiveFeedSubscriptionStatus.ACTIVE,
        )
        logger.info(
            "live_subscription_started",
            extra={"subscription_id": str(subscription.id), "provider": subscription.provider},
        )
        return subscription

    async def stop_subscription_runtime(self, subscription_id: UUID) -> LiveFeedSubscription:
        subscription = await self.set_subscription_status(
            subscription_id,
            LiveFeedSubscriptionStatus.STOPPED,
        )
        logger.info(
            "live_subscription_stopped",
            extra={"subscription_id": str(subscription.id), "provider": subscription.provider},
        )
        return subscription

    async def pause_subscription(self, subscription_id: UUID) -> LiveFeedSubscription:
        subscription = await self.set_subscription_status(
            subscription_id,
            LiveFeedSubscriptionStatus.PAUSED,
        )
        logger.info(
            "live_subscription_paused",
            extra={"subscription_id": str(subscription.id), "provider": subscription.provider},
        )
        return subscription

    async def resume_subscription(self, subscription_id: UUID) -> LiveFeedSubscription:
        return await self.start_subscription_runtime(subscription_id)

    async def mark_stale(self, subscription_id: UUID) -> LiveFeedSubscription:
        subscription = await self.set_subscription_status(
            subscription_id,
            LiveFeedSubscriptionStatus.STALE,
        )
        logger.warning(
            "live_subscription_stale",
            extra={"subscription_id": str(subscription.id), "provider": subscription.provider},
        )
        return subscription

    async def mark_failed(self, subscription_id: UUID, error_message: str) -> LiveFeedSubscription:
        subscription = await self.get_subscription(subscription_id)
        subscription.status = LiveFeedSubscriptionStatus.FAILED
        subscription.last_error = error_message[:1000]
        subscription.worker_id = None
        subscription.lease_expires_at = None
        await self.session.flush()
        await self.session.refresh(subscription)
        await self.session.commit()
        logger.error(
            "live_subscription_failed",
            extra={
                "subscription_id": str(subscription.id),
                "provider": subscription.provider,
                "error_message": subscription.last_error,
            },
        )
        return subscription

    async def update_heartbeat(self, subscription_id: UUID) -> LiveFeedSubscription:
        subscription = await self.get_subscription(subscription_id)
        subscription.last_message_at = utc_now()
        if subscription.status == LiveFeedSubscriptionStatus.STALE:
            subscription.status = LiveFeedSubscriptionStatus.ACTIVE
            subscription.last_error = None
        await self.session.flush()
        await self.session.refresh(subscription)
        await self.session.commit()
        return subscription

    async def update_final_candle_time(
        self,
        subscription_id: UUID,
        final_candle_at: datetime,
    ) -> LiveFeedSubscription:
        subscription = await self.get_subscription(subscription_id)
        subscription.last_final_candle_at = final_candle_at
        if subscription.status == LiveFeedSubscriptionStatus.STALE:
            subscription.status = LiveFeedSubscriptionStatus.ACTIVE
            subscription.last_error = None
        await self.session.flush()
        await self.session.refresh(subscription)
        await self.session.commit()
        return subscription

    async def list_runtime_candidates(self, limit: int = 500) -> list[LiveFeedSubscription]:
        return await self.repository.list_runtime_candidates(limit=limit)

    async def acquire_subscription_lease(
        self,
        subscription_id: UUID,
        worker_id: str,
        lease_seconds: float,
    ) -> LiveFeedSubscription | None:
        now = utc_now()
        subscription = await self.repository.acquire_subscription_lease(
            subscription_id=subscription_id,
            worker_id=worker_id,
            now=now,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
        )
        await self.session.commit()
        return subscription

    async def refresh_subscription_lease(
        self,
        subscription_id: UUID,
        worker_id: str,
        lease_seconds: float,
    ) -> bool:
        refreshed = await self.repository.refresh_subscription_lease(
            subscription_id=subscription_id,
            worker_id=worker_id,
            lease_expires_at=utc_now() + timedelta(seconds=lease_seconds),
        )
        await self.session.commit()
        return refreshed

    async def release_subscription_lease(self, subscription_id: UUID, worker_id: str) -> bool:
        released = await self.repository.release_subscription_lease(
            subscription_id=subscription_id,
            worker_id=worker_id,
        )
        await self.session.commit()
        return released

    async def list_subscription_events(
        self,
        subscription_id: UUID,
        limit: int,
        offset: int,
    ) -> list[LiveFeedEvent]:
        await self.get_subscription(subscription_id)
        return await self.repository.list_events(
            subscription_id=subscription_id,
            limit=limit,
            offset=offset,
        )

    async def ingest_provider_message(
        self,
        subscription_id: UUID,
        message: LiveProviderMessage,
    ) -> LiveFeedEvent:
        subscription = await self.get_subscription(subscription_id)
        event = await self.create_received_event(subscription, message)
        logger.info(
            "live_event_received",
            extra={
                "subscription_id": str(subscription.id),
                "provider": subscription.provider,
                "event_type": message.event_type.value,
            },
        )
        try:
            if subscription.status in {
                LiveFeedSubscriptionStatus.PAUSED,
                LiveFeedSubscriptionStatus.STOPPED,
            }:
                event.processing_status = LiveFeedEventProcessingStatus.IGNORED
                await self.session.commit()
                logger.info(
                    "live_event_processed",
                    extra={
                        "subscription_id": str(subscription.id),
                        "event_id": str(event.id),
                        "processing_status": event.processing_status,
                    },
                )
                return event
            provider = get_live_provider(subscription.provider)
            normalized_event = provider.normalize_message(message)
            event.event_type = normalized_event.event_type
            event.provider_timestamp = normalized_event.provider_timestamp
            event.payload_json = normalized_event.payload_json
            await self.process_received_event(
                subscription=subscription,
                event=event,
                normalized_event=normalized_event,
            )
            await self.session.commit()
        except (AppError, ValidationError) as error:
            await self.mark_event_failed(subscription, event, error)
            await self.session.commit()
        if event.processing_status == LiveFeedEventProcessingStatus.FAILED:
            logger.error(
                "live_event_failed",
                extra={
                    "subscription_id": str(subscription.id),
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "error_message": event.error_message,
                },
            )
        else:
            logger.info(
                "live_event_processed",
                extra={
                    "subscription_id": str(subscription.id),
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "processing_status": event.processing_status,
                },
            )
        return event

    async def refresh_stale_statuses(
        self,
        workspace_id: UUID | None,
        policy: LiveStalePolicy,
    ) -> int:
        subscriptions = await self.repository.list_subscriptions(
            limit=500,
            offset=0,
            workspace_id=workspace_id,
            status=LiveFeedSubscriptionStatus.ACTIVE,
        )
        now = utc_now()
        stale_count = 0
        for subscription in subscriptions:
            if subscription_is_stale(subscription, now, policy):
                subscription.status = LiveFeedSubscriptionStatus.STALE
                stale_count += 1
                logger.warning(
                    "live_subscription_stale",
                    extra={
                        "subscription_id": str(subscription.id),
                        "provider": subscription.provider,
                    },
                )
        await self.session.commit()
        return stale_count

    async def validate_symbol_and_source(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID,
    ) -> tuple[Symbol, DataSource]:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if not symbol.is_active:
            raise AppError(422, "inactive_symbol", "Inactive symbols cannot be subscribed")
        data_source = await self.data_source_repository.get_by_id(source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if data_source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )
        if data_source.source_type != DataSourceType.WEBSOCKET_LIVE:
            raise AppError(
                422,
                "invalid_live_source_type",
                "Live subscriptions require a websocket_live data source",
            )
        if data_source.status != DataSourceStatus.ACTIVE:
            raise AppError(422, "inactive_source", "Inactive sources cannot be subscribed")
        return symbol, data_source

    async def create_received_event(
        self,
        subscription: LiveFeedSubscription,
        message: LiveProviderMessage,
    ) -> LiveFeedEvent:
        received_at = utc_now()
        event = LiveFeedEvent(
            workspace_id=subscription.workspace_id,
            source_id=subscription.source_id,
            subscription_id=subscription.id,
            provider=subscription.provider,
            event_type=message.event_type,
            received_at=received_at,
            provider_timestamp=message.provider_timestamp,
            payload_json=message.payload_json,
            processing_status=LiveFeedEventProcessingStatus.RECEIVED,
        )
        subscription.last_message_at = received_at
        return await self.repository.create_event(event)

    async def process_received_event(
        self,
        subscription: LiveFeedSubscription,
        event: LiveFeedEvent,
        normalized_event: NormalizedLiveProviderEvent,
    ) -> None:
        if normalized_event.event_type == LiveFeedEventType.ERROR:
            event.processing_status = LiveFeedEventProcessingStatus.FAILED
            event.error_message = normalized_event.error_message or "Provider error"
            subscription.status = LiveFeedSubscriptionStatus.FAILED
            subscription.last_error = event.error_message
            return
        if normalized_event.event_type in {
            LiveFeedEventType.CANDLE_PARTIAL,
            LiveFeedEventType.CANDLE_FINAL,
        }:
            await self.process_candle_event(subscription, event, normalized_event)
            return
        if subscription.status == LiveFeedSubscriptionStatus.STALE:
            subscription.status = LiveFeedSubscriptionStatus.ACTIVE
            subscription.last_error = None
        event.processing_status = LiveFeedEventProcessingStatus.PROCESSED

    async def process_candle_event(
        self,
        subscription: LiveFeedSubscription,
        event: LiveFeedEvent,
        normalized_event: NormalizedLiveProviderEvent,
    ) -> None:
        if normalized_event.candle is None:
            raise AppError(422, "missing_live_candle", "Live candle event requires candle data")
        symbol, data_source = await self.validate_symbol_and_source(
            workspace_id=subscription.workspace_id,
            symbol_id=subscription.symbol_id,
            source_id=subscription.source_id,
        )
        candle = self.build_live_candle(subscription, event, normalized_event)
        validation_result = validate_candle(candle=candle, symbol=symbol, data_source=data_source)
        if not validation_result.is_valid:
            raise AppError(422, "invalid_live_candle", validation_result.issues[0].message)
        upsert_result = await self.candle_repository.upsert_normalized_candle(candle)
        if upsert_result.status == CandleUpsertStatus.CONFLICTING_FINAL:
            raise AppError(409, "conflicting_final_candle", upsert_result.message)
        if upsert_result.status == CandleUpsertStatus.IGNORED_LATE_PARTIAL:
            event.processing_status = LiveFeedEventProcessingStatus.IGNORED
            return
        if normalized_event.event_type == LiveFeedEventType.CANDLE_FINAL:
            subscription.last_final_candle_at = candle.timestamp
        if subscription.status == LiveFeedSubscriptionStatus.STALE:
            subscription.status = LiveFeedSubscriptionStatus.ACTIVE
            subscription.last_error = None
        event.processing_status = LiveFeedEventProcessingStatus.PROCESSED

    def build_live_candle(
        self,
        subscription: LiveFeedSubscription,
        event: LiveFeedEvent,
        normalized_event: NormalizedLiveProviderEvent,
    ) -> NormalizedCandleInput:
        if normalized_event.candle is None:
            raise AppError(422, "missing_live_candle", "Live candle event requires candle data")
        return normalize_candle_payload(
            payload=normalized_event.candle,
            workspace_id=subscription.workspace_id,
            symbol_id=subscription.symbol_id,
            source_id=subscription.source_id,
            timeframe=Timeframe(subscription.timeframe),
            is_final=normalized_event.event_type == LiveFeedEventType.CANDLE_FINAL,
            origin_type=CandleOriginType.LIVE_FEED,
            origin_reference_id=event.id,
        )

    async def mark_event_failed(
        self,
        subscription: LiveFeedSubscription,
        event: LiveFeedEvent,
        error: Exception,
    ) -> None:
        event.processing_status = LiveFeedEventProcessingStatus.FAILED
        event.error_message = self.error_message(error)
        subscription.status = LiveFeedSubscriptionStatus.FAILED
        subscription.last_error = event.error_message
        await self.session.flush()

    def error_message(self, error: Exception) -> str:
        if isinstance(error, AppError):
            return error.message
        if isinstance(error, ValidationError):
            return str(error.errors()[0]["msg"])
        return "Live event processing failed"
