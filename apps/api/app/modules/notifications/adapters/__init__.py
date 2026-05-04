from app.modules.notifications.adapters.base import (
    NotificationAdapter,
    NotificationAdapterRequest,
    NotificationAdapterResult,
)
from app.modules.notifications.adapters.discord import DiscordNotificationAdapter
from app.modules.notifications.adapters.email import EmailNotificationAdapter
from app.modules.notifications.adapters.telegram import TelegramNotificationAdapter
from app.modules.notifications.adapters.webhook import WebhookNotificationAdapter

__all__ = [
    "DiscordNotificationAdapter",
    "EmailNotificationAdapter",
    "NotificationAdapter",
    "NotificationAdapterRequest",
    "NotificationAdapterResult",
    "TelegramNotificationAdapter",
    "WebhookNotificationAdapter",
]
