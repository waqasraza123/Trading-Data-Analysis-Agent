import asyncio
import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import Settings
from app.modules.provider_credentials.models import (
    ProviderConnectionTestStatus,
    ProviderConnectionTestType,
    ProviderCredentialType,
)
from app.modules.provider_credentials.redaction import redact_payload


@dataclass(frozen=True)
class CredentialConnectionTestInput:
    provider: str
    credential_type: str
    test_type: ProviderConnectionTestType
    secret_ref_configured: bool
    request_metadata_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CredentialConnectionTestResult:
    status: ProviderConnectionTestStatus
    request_metadata_json: dict[str, Any]
    response_metadata_json: dict[str, Any]
    error_message: str | None = None


class ProviderCredentialConnectionTester:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def run_test(
        self,
        payload: CredentialConnectionTestInput,
    ) -> CredentialConnectionTestResult:
        test_type = self.effective_test_type(payload)
        request_metadata = self.safe_request_metadata(payload, test_type)
        if test_type == ProviderConnectionTestType.MOCK:
            return CredentialConnectionTestResult(
                status=ProviderConnectionTestStatus.PASSED,
                request_metadata_json=request_metadata,
                response_metadata_json={"provider": payload.provider, "mock": True},
            )
        if test_type == ProviderConnectionTestType.CONFIGURATION_ONLY:
            return self.configuration_only_result(payload, request_metadata)
        if test_type == ProviderConnectionTestType.AUTHENTICATED_ENDPOINT:
            return self.authenticated_endpoint_result(payload, request_metadata)
        if test_type == ProviderConnectionTestType.PUBLIC_ENDPOINT:
            return await self.public_endpoint_result(payload, request_metadata)
        return CredentialConnectionTestResult(
            status=ProviderConnectionTestStatus.SKIPPED,
            request_metadata_json=request_metadata,
            response_metadata_json={"reason": "unsupported_test_type"},
            error_message="Connection test type is not supported",
        )

    def effective_test_type(
        self,
        payload: CredentialConnectionTestInput,
    ) -> ProviderConnectionTestType:
        if payload.provider in {"mock", "mock_polling", "mock_live"}:
            return ProviderConnectionTestType.MOCK
        return payload.test_type

    def safe_request_metadata(
        self,
        payload: CredentialConnectionTestInput,
        test_type: ProviderConnectionTestType,
    ) -> dict[str, Any]:
        return {
            "provider": payload.provider,
            "credentialType": payload.credential_type,
            "testType": test_type.value,
            "secretRefConfigured": payload.secret_ref_configured,
            "metadata": redact_payload(payload.request_metadata_json),
        }

    def configuration_only_result(
        self,
        payload: CredentialConnectionTestInput,
        request_metadata: dict[str, Any],
    ) -> CredentialConnectionTestResult:
        if payload.credential_type == ProviderCredentialType.NONE_REQUIRED.value:
            return CredentialConnectionTestResult(
                status=ProviderConnectionTestStatus.PASSED,
                request_metadata_json=request_metadata,
                response_metadata_json={"reason": "credential_not_required"},
            )
        if payload.secret_ref_configured:
            return CredentialConnectionTestResult(
                status=ProviderConnectionTestStatus.PASSED,
                request_metadata_json=request_metadata,
                response_metadata_json={"reason": "credential_reference_configured"},
            )
        return CredentialConnectionTestResult(
            status=ProviderConnectionTestStatus.PROVIDER_NOT_CONFIGURED,
            request_metadata_json=request_metadata,
            response_metadata_json={"reason": "credential_reference_missing"},
            error_message="Provider credential reference is not configured",
        )

    def authenticated_endpoint_result(
        self,
        payload: CredentialConnectionTestInput,
        request_metadata: dict[str, Any],
    ) -> CredentialConnectionTestResult:
        if not payload.secret_ref_configured:
            return CredentialConnectionTestResult(
                status=ProviderConnectionTestStatus.PROVIDER_NOT_CONFIGURED,
                request_metadata_json=request_metadata,
                response_metadata_json={"reason": "credential_reference_missing"},
                error_message="Provider credential reference is not configured",
            )
        if not self.settings.provider_credential_allow_auth_tests:
            return CredentialConnectionTestResult(
                status=ProviderConnectionTestStatus.SKIPPED,
                request_metadata_json=request_metadata,
                response_metadata_json={"reason": "authenticated_tests_disabled"},
                error_message="Authenticated provider tests are disabled",
            )
        return CredentialConnectionTestResult(
            status=ProviderConnectionTestStatus.SKIPPED,
            request_metadata_json=request_metadata,
            response_metadata_json={"reason": "secret_resolution_not_implemented"},
            error_message="Secret manager resolution is not implemented in this phase",
        )

    async def public_endpoint_result(
        self,
        payload: CredentialConnectionTestInput,
        request_metadata: dict[str, Any],
    ) -> CredentialConnectionTestResult:
        if not self.settings.provider_credential_allow_public_tests:
            return CredentialConnectionTestResult(
                status=ProviderConnectionTestStatus.SKIPPED,
                request_metadata_json=request_metadata,
                response_metadata_json={"reason": "public_tests_disabled"},
                error_message="Public provider tests are disabled",
            )
        if payload.credential_type != ProviderCredentialType.NONE_REQUIRED.value:
            return CredentialConnectionTestResult(
                status=ProviderConnectionTestStatus.SKIPPED,
                request_metadata_json=request_metadata,
                response_metadata_json={"reason": "public_test_requires_none_required"},
                error_message="Public endpoint tests require none_required credentials",
            )
        endpoint = public_endpoint_for_provider(payload.provider)
        if endpoint is None:
            return CredentialConnectionTestResult(
                status=ProviderConnectionTestStatus.SKIPPED,
                request_metadata_json=request_metadata,
                response_metadata_json={"reason": "public_endpoint_not_configured"},
                error_message="No public endpoint test is configured for this provider",
            )
        return await asyncio.to_thread(
            execute_public_endpoint_test,
            endpoint,
            self.settings.provider_credential_test_timeout_seconds,
            request_metadata,
        )


def public_endpoint_for_provider(provider: str) -> str | None:
    normalized = provider.strip().lower()
    if normalized in {"binance", "binance_public_rest"}:
        return "https://api.binance.com/api/v3/ping"
    return None


def execute_public_endpoint_test(
    endpoint: str,
    timeout_seconds: int,
    request_metadata: dict[str, Any],
) -> CredentialConnectionTestResult:
    request = Request(endpoint, headers={"User-Agent": "trading-intelligence-provider-test/0.1"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read(1000).decode("utf-8", errors="replace")
            status_code = int(response.status)
            response_metadata: dict[str, Any] = {
                "statusCode": status_code,
                "endpoint": endpoint,
            }
            if response_body:
                try:
                    parsed = json.loads(response_body)
                    if isinstance(parsed, dict):
                        response_metadata["responseKeys"] = sorted(parsed.keys())[:20]
                except json.JSONDecodeError:
                    response_metadata["responseBytes"] = len(response_body.encode("utf-8"))
            if 200 <= status_code < 300:
                return CredentialConnectionTestResult(
                    status=ProviderConnectionTestStatus.PASSED,
                    request_metadata_json=request_metadata,
                    response_metadata_json=response_metadata,
                )
            return CredentialConnectionTestResult(
                status=ProviderConnectionTestStatus.FAILED,
                request_metadata_json=request_metadata,
                response_metadata_json=response_metadata,
                error_message="Public provider endpoint returned an error",
            )
    except HTTPError as error:
        return CredentialConnectionTestResult(
            status=ProviderConnectionTestStatus.FAILED,
            request_metadata_json=request_metadata,
            response_metadata_json={"endpoint": endpoint, "statusCode": error.code},
            error_message=f"Public provider endpoint returned HTTP status {error.code}",
        )
    except (URLError, TimeoutError):
        return CredentialConnectionTestResult(
            status=ProviderConnectionTestStatus.FAILED,
            request_metadata_json=request_metadata,
            response_metadata_json={"endpoint": endpoint},
            error_message="Public provider endpoint could not be reached",
        )
