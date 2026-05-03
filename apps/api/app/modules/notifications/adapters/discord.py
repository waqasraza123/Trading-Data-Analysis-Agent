from app.modules.notifications.adapters.base import (
    NotificationAdapter,
    NotificationAdapterRequest,
    NotificationAdapterResult,
)


class DiscordNotificationAdapter(NotificationAdapter):
    channel_type = "discord"

    async def deliver(self, request: NotificationAdapterRequest) -> NotificationAdapterResult:
        webhook_url = request.config_json.get("webhook_url")
        if not isinstance(webhook_url, str) or not webhook_url.strip():
            return NotificationAdapterResult(
                delivered=False,
                skipped=True,
                blocked=False,
                error_message="Discord webhook URL is not configured",
                metadata_json={"adapter": "discord", "reason": "discord_webhook_url_missing"},
            )
        return NotificationAdapterResult(
            delivered=False,
            skipped=True,
            blocked=False,
            error_message="Discord webhook delivery is a safe stub in this phase",
            metadata_json={"adapter": "discord", "reason": "discord_adapter_stub"},
        )
