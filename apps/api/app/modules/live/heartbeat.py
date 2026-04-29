from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modules.live.models import LiveFeedSubscription


@dataclass(frozen=True)
class LiveStalePolicy:
    message_stale_after_seconds: int = 180
    final_candle_stale_after_seconds: int = 300


def subscription_is_stale(
    subscription: LiveFeedSubscription,
    now: datetime,
    policy: LiveStalePolicy,
) -> bool:
    message_reference = subscription.last_message_at or subscription.created_at
    if message_reference + timedelta(seconds=policy.message_stale_after_seconds) < now:
        return True
    final_reference = subscription.last_final_candle_at or subscription.created_at
    return final_reference + timedelta(seconds=policy.final_candle_stale_after_seconds) < now
