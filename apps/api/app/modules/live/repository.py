from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import Select, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.live.models import (
    LiveFeedEvent,
    LiveFeedSubscription,
    LiveFeedSubscriptionStatus,
)


class LiveRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_subscription(
        self,
        subscription: LiveFeedSubscription,
    ) -> LiveFeedSubscription:
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def get_subscription(self, subscription_id: UUID) -> LiveFeedSubscription | None:
        return await self.session.get(LiveFeedSubscription, subscription_id)

    async def list_subscriptions(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        status: str | None = None,
        provider: str | None = None,
        symbol_id: UUID | None = None,
    ) -> list[LiveFeedSubscription]:
        statement: Select[tuple[LiveFeedSubscription]] = (
            select(LiveFeedSubscription)
            .order_by(LiveFeedSubscription.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(LiveFeedSubscription.workspace_id == workspace_id)
        if status is not None:
            statement = statement.where(LiveFeedSubscription.status == status)
        if provider is not None:
            statement = statement.where(LiveFeedSubscription.provider == provider)
        if symbol_id is not None:
            statement = statement.where(LiveFeedSubscription.symbol_id == symbol_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_runtime_candidates(self, limit: int) -> list[LiveFeedSubscription]:
        statement: Select[tuple[LiveFeedSubscription]] = (
            select(LiveFeedSubscription)
            .where(LiveFeedSubscription.status == LiveFeedSubscriptionStatus.ACTIVE)
            .order_by(LiveFeedSubscription.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def acquire_subscription_lease(
        self,
        subscription_id: UUID,
        worker_id: str,
        now: datetime,
        lease_expires_at: datetime,
    ) -> LiveFeedSubscription | None:
        statement = (
            update(LiveFeedSubscription)
            .where(
                LiveFeedSubscription.id == subscription_id,
                LiveFeedSubscription.status == LiveFeedSubscriptionStatus.ACTIVE,
                or_(
                    LiveFeedSubscription.worker_id.is_(None),
                    LiveFeedSubscription.worker_id == worker_id,
                    LiveFeedSubscription.lease_expires_at.is_(None),
                    LiveFeedSubscription.lease_expires_at <= now,
                ),
            )
            .values(worker_id=worker_id, lease_expires_at=lease_expires_at)
            .returning(LiveFeedSubscription)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def refresh_subscription_lease(
        self,
        subscription_id: UUID,
        worker_id: str,
        lease_expires_at: datetime,
    ) -> bool:
        statement = (
            update(LiveFeedSubscription)
            .where(
                LiveFeedSubscription.id == subscription_id,
                LiveFeedSubscription.worker_id == worker_id,
            )
            .values(lease_expires_at=lease_expires_at)
        )
        result = cast(CursorResult[object], await self.session.execute(statement))
        return result.rowcount > 0

    async def release_subscription_lease(
        self,
        subscription_id: UUID,
        worker_id: str,
    ) -> bool:
        statement = (
            update(LiveFeedSubscription)
            .where(
                LiveFeedSubscription.id == subscription_id,
                LiveFeedSubscription.worker_id == worker_id,
            )
            .values(worker_id=None, lease_expires_at=None)
        )
        result = cast(CursorResult[object], await self.session.execute(statement))
        return result.rowcount > 0

    async def create_event(self, event: LiveFeedEvent) -> LiveFeedEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list_events(
        self,
        subscription_id: UUID,
        limit: int,
        offset: int,
    ) -> list[LiveFeedEvent]:
        statement: Select[tuple[LiveFeedEvent]] = (
            select(LiveFeedEvent)
            .where(LiveFeedEvent.subscription_id == subscription_id)
            .order_by(LiveFeedEvent.received_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
