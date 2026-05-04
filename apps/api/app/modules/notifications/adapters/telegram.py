from app.modules.notifications.adapters.base import (
    NotificationAdapter,
    NotificationAdapterRequest,
    NotificationAdapterResult,
)


class TelegramNotificationAdapter(NotificationAdapter):
    channel_type = "telegram"

    async def deliver(self, request: NotificationAdapterRequest) -> NotificationAdapterResult:
        chat_id = request.config_json.get("chat_id")
        if not isinstance(chat_id, str) or not chat_id.strip():
            return NotificationAdapterResult(
                delivered=False,
                skipped=True,
                blocked=False,
                error_message="Telegram chat ID is not configured",
                metadata_json={"adapter": "telegram", "reason": "telegram_chat_id_missing"},
            )
        return NotificationAdapterResult(
            delivered=False,
            skipped=True,
            blocked=False,
            error_message=(
                "Telegram delivery requires bot token secret resolution before it can send"
            ),
            metadata_json={
                "adapter": "telegram",
                "reason": "telegram_secret_resolution_not_available",
            },
        )
