from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.notifications.adapters.base import NotificationAdapterRequest
from app.modules.notifications.adapters.webhook import WebhookNotificationAdapter
from app.modules.notifications.dedupe import build_notification_dedupe_key
from app.modules.notifications.models import BackendNotificationEventType, NotificationEventSeverity
from app.modules.notifications.quiet_hours import evaluate_quiet_hours
from app.modules.notifications.safety import sanitize_notification_delivery_payload
from app.modules.safety_policies.schemas import SafetyStatus


def test_delivery_safety_blocks_trade_instruction_language() -> None:
    result = sanitize_notification_delivery_payload(
        title="Review only",
        summary="Do not buy now",
        payload_json={"safe": True},
        max_payload_bytes=16000,
    )

    assert result.safety_status == SafetyStatus.BLOCKED
    assert "buy" in result.blocked_terms
    assert result.payload_json == {}


def test_delivery_safety_redacts_secrets_raw_series_and_llm_output() -> None:
    result = sanitize_notification_delivery_payload(
        title="Data quality degraded",
        summary="Review the stored data quality finding.",
        payload_json={
            "api_key": "secret",
            "raw_candles": [{"open": "1"}],
            "raw_llm_output": "unsafe",
            "safe": "kept",
        },
        max_payload_bytes=16000,
    )

    assert result.safety_status == SafetyStatus.REDACTED
    assert result.payload_json["api_key"] == "[redacted]"
    assert result.payload_json["raw_candles"] == "[redacted]"
    assert result.payload_json["raw_llm_output"] == "[redacted]"
    assert result.payload_json["safe"] == "kept"


def test_dedupe_key_uses_workspace_source_event_and_severity() -> None:
    workspace_id = uuid4()
    source_id = uuid4()

    first = build_notification_dedupe_key(
        workspace_id=workspace_id,
        event_type=BackendNotificationEventType.OUTCOME_EVALUATED,
        source_type="outcome",
        source_id=source_id,
        severity=NotificationEventSeverity.HIGH,
    )
    second = build_notification_dedupe_key(
        workspace_id=workspace_id,
        event_type=BackendNotificationEventType.OUTCOME_EVALUATED,
        source_type="outcome",
        source_id=source_id,
        severity=NotificationEventSeverity.HIGH,
    )

    assert first == second
    assert first.startswith("notification-event:")


def test_quiet_hours_detects_overnight_hold_window() -> None:
    decision = evaluate_quiet_hours(
        {
            "enabled": True,
            "timezone": "UTC",
            "start": "22:00",
            "end": "07:00",
            "behavior": "hold",
        },
        now=datetime(2026, 5, 3, 23, 30, tzinfo=UTC),
        default_timezone="UTC",
    )

    assert decision.inside_quiet_hours is True
    assert decision.behavior == "hold"


@pytest.mark.asyncio
async def test_webhook_adapter_skips_without_target_url() -> None:
    adapter = WebhookNotificationAdapter()

    result = await adapter.deliver(
        NotificationAdapterRequest(
            workspace_id=uuid4(),
            event_id=uuid4(),
            channel_id=uuid4(),
            event_type="data_quality.degraded",
            severity="high",
            title="Data quality degraded",
            summary="Review the stored data quality finding.",
            payload_json={},
            config_json={},
            secret_ref=None,
            timeout_seconds=1,
            user_agent="test-agent",
        )
    )

    assert result.skipped is True
    assert result.delivered is False
    assert result.metadata_json["reason"] == "webhook_target_url_missing"
