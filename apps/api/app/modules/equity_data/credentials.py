import json
import os
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.modules.equity_data.adapters import get_equity_data_provider
from app.modules.provider_credentials.models import ProviderCredentialStatus
from app.modules.provider_credentials.repository import ProviderCredentialRepository


@dataclass(frozen=True)
class EquityCredentialResolution:
    provider_name: str
    credential_ref_id: UUID | None
    status: str
    ready: bool
    message: str
    secret_material_available: bool = False
    secret_values: dict[str, str] = field(default_factory=dict, repr=False)


class EquityCredentialResolver:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: ProviderCredentialRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or ProviderCredentialRepository(session)

    async def resolve_credential_ref(
        self,
        provider_name: str,
        credential_ref_id: UUID | None,
        workspace_id: UUID,
    ) -> EquityCredentialResolution:
        provider = get_equity_data_provider(provider_name)
        if not provider.requires_credential_ref():
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=None,
                status="no_secret_required",
                ready=True,
                message="Provider does not require a credential reference",
            )
        if not self.settings.equity_data_allow_external_requests:
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=credential_ref_id,
                status="external_requests_disabled",
                ready=False,
                message="External provider requests are disabled",
            )
        if credential_ref_id is None:
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=None,
                status="missing_credential_ref",
                ready=False,
                message="Credential reference is required",
            )
        credential = await self.repository.get_credential_ref(credential_ref_id)
        if credential is None:
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=credential_ref_id,
                status="credential_ref_not_found",
                ready=False,
                message="Credential reference was not found",
            )
        if credential.workspace_id != workspace_id:
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=credential_ref_id,
                status="credential_ref_workspace_mismatch",
                ready=False,
                message="Credential reference does not belong to this workspace",
            )
        if credential.provider != provider.key():
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=credential_ref_id,
                status="credential_ref_provider_mismatch",
                ready=False,
                message="Credential reference belongs to a different provider",
            )
        if credential.status != ProviderCredentialStatus.ACTIVE.value:
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=credential_ref_id,
                status="credential_ref_inactive",
                ready=False,
                message="Credential reference is not active",
            )
        if not self.settings.equity_data_env_secret_resolution_enabled:
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=credential_ref_id,
                status="secret_resolution_disabled",
                ready=False,
                message="Environment secret resolution is disabled",
            )
        secret_values = resolve_environment_secret_ref(credential.secret_ref, provider.key())
        if not secret_values:
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=credential_ref_id,
                status="secret_material_missing",
                ready=False,
                message="Credential reference secret material is unavailable",
            )
        missing = missing_provider_secret_keys(provider.key(), secret_values)
        if missing:
            return EquityCredentialResolution(
                provider_name=provider.key(),
                credential_ref_id=credential_ref_id,
                status="secret_material_incomplete",
                ready=False,
                message=f"Credential reference is missing required material: {', '.join(missing)}",
            )
        return EquityCredentialResolution(
            provider_name=provider.key(),
            credential_ref_id=credential_ref_id,
            status="ready",
            ready=True,
            message="Credential reference secret material is available",
            secret_material_available=True,
            secret_values=secret_values,
        )


def resolve_environment_secret_ref(secret_ref: str | None, provider_name: str) -> dict[str, str]:
    if not secret_ref:
        return {}
    normalized = secret_ref.strip()
    if normalized.startswith("env-json:"):
        env_name = normalized.removeprefix("env-json:").strip()
        raw_value = os.environ.get(env_name)
        if not raw_value:
            return {}
        try:
            decoded = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        if not isinstance(decoded, dict):
            return {}
        return normalize_secret_values(decoded)
    if normalized.startswith("env-pair:"):
        env_names = [
            item.strip()
            for item in normalized.removeprefix("env-pair:").split(",")
            if item.strip()
        ]
        if len(env_names) != 2:
            return {}
        first_value = os.environ.get(env_names[0])
        second_value = os.environ.get(env_names[1])
        if not first_value or not second_value:
            return {}
        return {"api_key_id": first_value, "api_secret_key": second_value}
    if normalized.startswith("env://"):
        env_name = normalized.removeprefix("env://").strip("/")
    elif normalized.startswith("env:"):
        env_name = normalized.removeprefix("env:").strip()
    else:
        return {}
    raw_value = os.environ.get(env_name)
    if not raw_value:
        return {}
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        decoded = raw_value
    if isinstance(decoded, dict):
        return normalize_secret_values(decoded)
    if provider_name == "alpaca":
        return {"api_key_id": str(decoded)}
    return {"api_key": str(decoded)}


def normalize_secret_values(value: dict[str, Any]) -> dict[str, str]:
    aliases = {
        "apiKey": "api_key",
        "api_key": "api_key",
        "key": "api_key",
        "token": "api_key",
        "keyId": "api_key_id",
        "key_id": "api_key_id",
        "apiKeyId": "api_key_id",
        "api_key_id": "api_key_id",
        "APCA_API_KEY_ID": "api_key_id",
        "secret": "api_secret_key",
        "secretKey": "api_secret_key",
        "secret_key": "api_secret_key",
        "apiSecretKey": "api_secret_key",
        "api_secret_key": "api_secret_key",
        "APCA_API_SECRET_KEY": "api_secret_key",
    }
    normalized: dict[str, str] = {}
    for key, raw_value in value.items():
        mapped_key = aliases.get(str(key))
        if mapped_key is None or raw_value in {None, ""}:
            continue
        normalized[mapped_key] = str(raw_value)
    return normalized


def missing_provider_secret_keys(provider_name: str, values: dict[str, str]) -> list[str]:
    if provider_name == "alpaca":
        required = ("api_key_id", "api_secret_key")
    else:
        required = ("api_key",)
    return [key for key in required if not values.get(key)]
