from typing import Any

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.modules.live.models import LiveFeedSubscription, LiveFeedSubscriptionStatus


class LiveWorkerHealth(BaseModel):
    status: str
    active_subscriptions: int
    leased_subscriptions: int
    stale_subscriptions: int
    expired_leases: int


async def collect_live_worker_health(session: AsyncSession) -> LiveWorkerHealth:
    now = utc_now()
    active_subscriptions = await scalar_count(
        session,
        select(func.count())
        .select_from(LiveFeedSubscription)
        .where(LiveFeedSubscription.status == LiveFeedSubscriptionStatus.ACTIVE),
    )
    leased_subscriptions = await scalar_count(
        session,
        select(func.count())
        .select_from(LiveFeedSubscription)
        .where(
            LiveFeedSubscription.worker_id.is_not(None),
            LiveFeedSubscription.lease_expires_at > now,
        ),
    )
    stale_subscriptions = await scalar_count(
        session,
        select(func.count())
        .select_from(LiveFeedSubscription)
        .where(LiveFeedSubscription.status == LiveFeedSubscriptionStatus.STALE),
    )
    expired_leases = await scalar_count(
        session,
        select(func.count())
        .select_from(LiveFeedSubscription)
        .where(
            LiveFeedSubscription.worker_id.is_not(None),
            LiveFeedSubscription.lease_expires_at.is_not(None),
            LiveFeedSubscription.lease_expires_at <= now,
        ),
    )
    status = "healthy"
    if expired_leases:
        status = "degraded"
    if active_subscriptions and leased_subscriptions == 0:
        status = "not_running"
    return LiveWorkerHealth(
        status=status,
        active_subscriptions=active_subscriptions,
        leased_subscriptions=leased_subscriptions,
        stale_subscriptions=stale_subscriptions,
        expired_leases=expired_leases,
    )


async def scalar_count(session: AsyncSession, statement: Select[Any]) -> int:
    result = await session.execute(statement)
    value = result.scalar_one()
    if value is None:
        return 0
    return int(value)
