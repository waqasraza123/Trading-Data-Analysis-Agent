from dataclasses import dataclass
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
        return EquityCredentialResolution(
            provider_name=provider.key(),
            credential_ref_id=credential_ref_id,
            status="secret_manager_not_configured",
            ready=False,
            message="Credential reference metadata exists but secret resolution is not configured",
        )
