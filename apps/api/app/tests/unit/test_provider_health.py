from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.config import Settings
from app.modules.provider_health.models import ProviderHealthFreshnessLabel
from app.modules.provider_health.service import ProviderHealthService, count_consecutive_failures
from app.modules.provider_polling.models import ProviderPollingRequestStatus


def test_provider_health_freshness_uses_configured_thresholds() -> None:
    service = ProviderHealthService(session=None, settings=Settings(_env_file=None))
    fresh_time = datetime.now(UTC) - timedelta(seconds=120)
    delayed_time = datetime.now(UTC) - timedelta(seconds=240)
    stale_time = datetime.now(UTC) - timedelta(seconds=420)

    assert (
        service.determine_freshness_label(fresh_time, "1m")
        == ProviderHealthFreshnessLabel.FRESH
    )
    assert (
        service.determine_freshness_label(delayed_time, "1m")
        == ProviderHealthFreshnessLabel.DELAYED
    )
    assert (
        service.determine_freshness_label(stale_time, "1m")
        == ProviderHealthFreshnessLabel.STALE
    )


def test_provider_health_counts_consecutive_failures_until_success() -> None:
    requests = [
        SimpleNamespace(status=ProviderPollingRequestStatus.FAILED.value),
        SimpleNamespace(status=ProviderPollingRequestStatus.FAILED.value),
        SimpleNamespace(status=ProviderPollingRequestStatus.COMPLETED.value),
        SimpleNamespace(status=ProviderPollingRequestStatus.FAILED.value),
    ]

    assert count_consecutive_failures(requests) == 2
