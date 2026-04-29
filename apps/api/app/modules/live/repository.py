from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.live.models import LiveFeedEvent, LiveFeedSubscription


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
