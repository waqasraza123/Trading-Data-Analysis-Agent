import asyncio
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.modules.notifications.adapters.base import (
    NotificationAdapter,
    NotificationAdapterRequest,
    NotificationAdapterResult,
)


class WebhookNotificationAdapter(NotificationAdapter):
    channel_type = "webhook"

    async def deliver(self, request: NotificationAdapterRequest) -> NotificationAdapterResult:
        target_url = request.config_json.get("target_url") or request.config_json.get("url")
        if not isinstance(target_url, str) or not target_url.strip():
            return NotificationAdapterResult(
                delivered=False,
                skipped=True,
                blocked=False,
                error_message="Webhook target URL is not configured",
                metadata_json={"reason": "webhook_target_url_missing"},
            )
        normalized_url = target_url.strip()
        if not is_allowed_webhook_url(normalized_url):
            return NotificationAdapterResult(
                delivered=False,
                skipped=False,
                blocked=True,
                error_message="Webhook target URL must use http or https",
                metadata_json={"reason": "webhook_target_url_not_allowed"},
            )
        body = {
            "id": str(request.event_id),
            "workspaceId": str(request.workspace_id),
            "eventType": request.event_type,
            "severity": request.severity,
            "title": request.title,
            "summary": request.summary,
            "payload": request.payload_json,
        }
        return await asyncio.to_thread(
            post_webhook,
            normalized_url,
            body,
            request.timeout_seconds,
            request.user_agent,
        )


def is_allowed_webhook_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def post_webhook(
    url: str,
    body: dict[str, object],
    timeout_seconds: int,
    user_agent: str,
) -> NotificationAdapterResult:
    encoded_body = json.dumps(body, default=str, sort_keys=True).encode("utf-8")
    request = Request(
        url,
        data=encoded_body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read(1000).decode("utf-8", errors="replace")
            status_code = int(response.status)
            return NotificationAdapterResult(
                delivered=200 <= status_code < 300,
                skipped=False,
                blocked=False,
                response_status_code=status_code,
                response_body_excerpt=response_body[:1000] or None,
                error_message=None if 200 <= status_code < 300 else "Webhook returned an error",
                metadata_json={"adapter": "webhook"},
            )
    except HTTPError as error:
        response_body = error.read(1000).decode("utf-8", errors="replace")
        return NotificationAdapterResult(
            delivered=False,
            skipped=False,
            blocked=False,
            response_status_code=error.code,
            response_body_excerpt=response_body[:1000] or None,
            error_message=f"Webhook request failed with HTTP status {error.code}",
            metadata_json={"adapter": "webhook"},
        )
    except URLError as error:
        return NotificationAdapterResult(
            delivered=False,
            skipped=False,
            blocked=False,
            error_message="Webhook request failed before a response was received",
            metadata_json={"adapter": "webhook", "reason": str(error.reason)},
        )
    except TimeoutError:
        return NotificationAdapterResult(
            delivered=False,
            skipped=False,
            blocked=False,
            error_message="Webhook request timed out",
            metadata_json={"adapter": "webhook"},
        )
