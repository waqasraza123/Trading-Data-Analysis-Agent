from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.config import Settings
from app.modules.daily_workflows.models import DailyWorkflowStepKey, DailyWorkflowType
from app.modules.daily_workflows.runner import (
    DAILY_WORKFLOW_STEP_ORDER,
    should_create_provider_polling_requests,
)
from app.modules.daily_workflows.schemas import DailyWorkflowOptions, DailyWorkflowRunRequest


def test_daily_workflow_step_order_is_stable() -> None:
    assert DAILY_WORKFLOW_STEP_ORDER == [
        DailyWorkflowStepKey.PROVIDER_HEALTH_REFRESH,
        DailyWorkflowStepKey.GAP_RECOVERY_PREPARE,
        DailyWorkflowStepKey.SCHEDULED_SCAN_RUN,
        DailyWorkflowStepKey.SETUP_CONTEXT_GENERATE,
        DailyWorkflowStepKey.SIGNAL_PRIORITY_SCORE,
        DailyWorkflowStepKey.MARKET_MEMORY_REFRESH,
        DailyWorkflowStepKey.SIGNAL_DIGEST_GENERATE,
        DailyWorkflowStepKey.DAILY_BRIEF_GENERATE,
    ]


def test_provider_polling_requires_request_and_setting() -> None:
    disabled_settings = Settings(_env_file=None, daily_workflow_enable_provider_polling=False)
    enabled_settings = Settings(_env_file=None, daily_workflow_enable_provider_polling=True)

    assert (
        should_create_provider_polling_requests(
            DailyWorkflowOptions(allow_provider_polling=True),
            disabled_settings,
        )
        is False
    )
    assert (
        should_create_provider_polling_requests(
            DailyWorkflowOptions(allow_provider_polling=False),
            enabled_settings,
        )
        is False
    )
    assert (
        should_create_provider_polling_requests(
            DailyWorkflowOptions(allow_provider_polling=True),
            enabled_settings,
        )
        is True
    )


def test_watchlist_scan_requires_watchlist_id() -> None:
    with pytest.raises(ValueError, match="watchlist_id"):
        DailyWorkflowRunRequest(
            workspace_id=uuid4(),
            workflow_type=DailyWorkflowType.WATCHLIST_SCAN,
        )


def test_period_start_must_precede_period_end() -> None:
    now = datetime(2026, 5, 3, 12, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="period_start"):
        DailyWorkflowRunRequest(
            workspace_id=uuid4(),
            period_start=now,
            period_end=now - timedelta(minutes=1),
        )
