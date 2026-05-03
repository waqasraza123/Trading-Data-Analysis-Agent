import hashlib
from uuid import UUID

from app.modules.notifications.models import BackendNotificationEventType, NotificationEventSeverity


def build_notification_dedupe_key(
    workspace_id: UUID,
    event_type: BackendNotificationEventType,
    source_type: str,
    source_id: UUID,
    severity: NotificationEventSeverity,
) -> str:
    raw_key = "|".join(
        [
            str(workspace_id),
            event_type.value,
            source_type.strip().lower(),
            str(source_id),
            severity.value,
        ]
    )
    return f"notification-event:{hashlib.sha256(raw_key.encode('utf-8')).hexdigest()[:40]}"
