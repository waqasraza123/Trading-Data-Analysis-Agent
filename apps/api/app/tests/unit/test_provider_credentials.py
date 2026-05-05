from app.config import Settings
from app.modules.provider_credentials.connection_tests import (
    CredentialConnectionTestInput,
    ProviderCredentialConnectionTester,
)
from app.modules.provider_credentials.models import (
    ProviderConnectionTestStatus,
    ProviderConnectionTestType,
    ProviderCredentialType,
)
from app.modules.provider_credentials.redaction import find_sensitive_payload_paths, redact_payload


def test_provider_credential_redaction_removes_secret_values() -> None:
    payload = {
        "region": "us",
        "token": "raw-token",
        "nested": {"authorization": "Bearer raw"},
        "fingerprint": "abc123",
    }

    assert redact_payload(payload) == {
        "region": "us",
        "token": "[redacted]",
        "nested": {"authorization": "[redacted]"},
        "fingerprint": "abc123",
    }
    assert find_sensitive_payload_paths(payload) == ["$.token", "$.nested.authorization"]


async def test_mock_connection_test_passes_without_secret() -> None:
    tester = ProviderCredentialConnectionTester(Settings(_env_file=None))

    result = await tester.run_test(
        CredentialConnectionTestInput(
            provider="mock",
            credential_type=ProviderCredentialType.NONE_REQUIRED.value,
            test_type=ProviderConnectionTestType.CONFIGURATION_ONLY,
            secret_ref_configured=False,
        )
    )

    assert result.status == ProviderConnectionTestStatus.PASSED
    assert result.response_metadata_json["mock"] is True


async def test_authenticated_connection_test_skips_when_auth_tests_disabled() -> None:
    tester = ProviderCredentialConnectionTester(
        Settings(_env_file=None, provider_credential_allow_auth_tests=False)
    )

    result = await tester.run_test(
        CredentialConnectionTestInput(
            provider="polygon",
            credential_type=ProviderCredentialType.API_KEY.value,
            test_type=ProviderConnectionTestType.AUTHENTICATED_ENDPOINT,
            secret_ref_configured=True,
        )
    )

    assert result.status == ProviderConnectionTestStatus.SKIPPED
    assert result.response_metadata_json["reason"] == "authenticated_tests_disabled"


async def test_configuration_only_reports_missing_credential_reference() -> None:
    tester = ProviderCredentialConnectionTester(Settings(_env_file=None))

    result = await tester.run_test(
        CredentialConnectionTestInput(
            provider="polygon",
            credential_type=ProviderCredentialType.API_KEY.value,
            test_type=ProviderConnectionTestType.CONFIGURATION_ONLY,
            secret_ref_configured=False,
        )
    )

    assert result.status == ProviderConnectionTestStatus.PROVIDER_NOT_CONFIGURED
    assert "not configured" in str(result.error_message)
