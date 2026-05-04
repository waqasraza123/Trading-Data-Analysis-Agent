from app.modules.notifications.adapters.base import (
    NotificationAdapter,
    NotificationAdapterRequest,
    NotificationAdapterResult,
)


class EmailNotificationAdapter(NotificationAdapter):
    channel_type = "email"

    async def deliver(self, request: NotificationAdapterRequest) -> NotificationAdapterResult:
        provider = request.config_json.get("provider")
        if provider not in {"smtp"}:
            return NotificationAdapterResult(
                delivered=False,
                skipped=True,
                blocked=False,
                error_message="Email provider is not configured",
                metadata_json={"adapter": "email", "reason": "email_provider_not_configured"},
            )
        return NotificationAdapterResult(
            delivered=False,
            skipped=True,
            blocked=False,
            error_message="SMTP delivery requires secret resolution before it can send",
            metadata_json={"adapter": "email", "reason": "smtp_secret_resolution_not_available"},
        )
