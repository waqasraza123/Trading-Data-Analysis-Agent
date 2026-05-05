import hashlib
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.provider_credentials.connection_tests import (
    CredentialConnectionTestInput,
    CredentialConnectionTestResult,
    ProviderCredentialConnectionTester,
)
from app.modules.provider_credentials.models import (
    ProviderConnectionTest,
    ProviderConnectionTestStatus,
    ProviderConnectionTestType,
    ProviderCredentialRef,
    ProviderCredentialStatus,
    ProviderCredentialType,
)
from app.modules.provider_credentials.redaction import (
    find_sensitive_payload_paths,
    redact_payload,
)
from app.modules.provider_credentials.repository import ProviderCredentialRepository
from app.modules.provider_credentials.schemas import (
    ProviderConfigurationTestRequest,
    ProviderCredentialRefCreate,
    ProviderCredentialRefRead,
    ProviderCredentialRefUpdate,
)


class ProviderCredentialService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repository = ProviderCredentialRepository(session)
        self.connection_tester = ProviderCredentialConnectionTester(settings)

    async def create_credential_ref(
        self,
        payload: ProviderCredentialRefCreate,
    ) -> ProviderCredentialRef:
        self.validate_public_metadata(payload.public_metadata_json)
        status = self.effective_status(
            credential_type=payload.credential_type,
            status=payload.status,
            secret_ref=payload.secret_ref,
        )
        credential_ref = ProviderCredentialRef(
            workspace_id=payload.workspace_id,
            name=payload.name.strip(),
            provider=payload.provider,
            credential_type=payload.credential_type.value,
            status=status.value,
            secret_ref=payload.secret_ref.strip() if payload.secret_ref is not None else None,
            public_metadata_json=redact_payload(payload.public_metadata_json),
        )
        try:
            created = await self.repository.create_credential_ref(credential_ref)
            await self.session.commit()
            await self.session.refresh(created)
            return created
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "provider_credential_ref_conflict",
                "Provider credential reference could not be created",
            ) from error

    async def list_credential_refs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        provider: str | None = None,
        status: ProviderCredentialStatus | None = None,
        credential_type: ProviderCredentialType | None = None,
    ) -> list[ProviderCredentialRef]:
        return await self.repository.list_credential_refs(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            provider=provider,
            status=status.value if status is not None else None,
            credential_type=credential_type.value if credential_type is not None else None,
        )

    async def get_credential_ref(self, credential_ref_id: UUID) -> ProviderCredentialRef:
        credential_ref = await self.repository.get_credential_ref(credential_ref_id)
        if credential_ref is None:
            raise AppError(
                404,
                "provider_credential_ref_not_found",
                "Provider credential reference not found",
            )
        return credential_ref

    async def update_credential_ref(
        self,
        credential_ref_id: UUID,
        payload: ProviderCredentialRefUpdate,
    ) -> ProviderCredentialRef:
        credential_ref = await self.get_credential_ref(credential_ref_id)
        previous_secret_ref = credential_ref.secret_ref
        updates = payload.model_dump(exclude_unset=True, mode="python")
        if "public_metadata_json" in updates and payload.public_metadata_json is not None:
            self.validate_public_metadata(payload.public_metadata_json)
            credential_ref.public_metadata_json = redact_payload(payload.public_metadata_json)
        if payload.name is not None:
            credential_ref.name = payload.name.strip()
        if payload.provider is not None:
            credential_ref.provider = payload.provider
        if payload.credential_type is not None:
            credential_ref.credential_type = payload.credential_type.value
        if payload.status is not None:
            credential_ref.status = payload.status.value
        if "secret_ref" in updates:
            credential_ref.secret_ref = (
                payload.secret_ref.strip() if payload.secret_ref is not None else None
            )
            if credential_ref.secret_ref != previous_secret_ref:
                credential_ref.rotated_at = utc_now()
        credential_ref.status = self.effective_status(
            credential_type=ProviderCredentialType(credential_ref.credential_type),
            status=ProviderCredentialStatus(credential_ref.status),
            secret_ref=credential_ref.secret_ref,
        ).value
        try:
            await self.session.flush()
            await self.session.refresh(credential_ref)
            await self.session.commit()
            return credential_ref
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "provider_credential_ref_conflict",
                "Provider credential reference could not be updated",
            ) from error

    async def pause_credential_ref(self, credential_ref_id: UUID) -> ProviderCredentialRef:
        credential_ref = await self.get_credential_ref(credential_ref_id)
        if credential_ref.status == ProviderCredentialStatus.REVOKED.value:
            raise AppError(
                409,
                "provider_credential_ref_revoked",
                "Revoked credential references cannot be paused",
            )
        credential_ref.status = ProviderCredentialStatus.PAUSED.value
        await self.session.flush()
        await self.session.refresh(credential_ref)
        await self.session.commit()
        return credential_ref

    async def revoke_credential_ref(self, credential_ref_id: UUID) -> ProviderCredentialRef:
        credential_ref = await self.get_credential_ref(credential_ref_id)
        credential_ref.status = ProviderCredentialStatus.REVOKED.value
        await self.session.flush()
        await self.session.refresh(credential_ref)
        await self.session.commit()
        return credential_ref

    async def test_credential_ref(
        self,
        credential_ref_id: UUID,
        test_type: ProviderConnectionTestType | None = None,
    ) -> ProviderConnectionTest:
        credential_ref = await self.get_credential_ref(credential_ref_id)
        effective_test_type = test_type or self.default_test_type(credential_ref)
        result = await self.connection_tester.run_test(
            CredentialConnectionTestInput(
                provider=credential_ref.provider,
                credential_type=credential_ref.credential_type,
                test_type=effective_test_type,
                secret_ref_configured=credential_ref.secret_ref is not None,
            )
        )
        connection_test = await self.record_connection_test(
            workspace_id=credential_ref.workspace_id,
            credential_ref_id=credential_ref.id,
            provider=credential_ref.provider,
            test_type=effective_test_type,
            result=result,
        )
        credential_ref.last_test_status = connection_test.status
        credential_ref.last_tested_at = connection_test.created_at
        credential_ref.last_error_message = connection_test.error_message
        if connection_test.status == ProviderConnectionTestStatus.FAILED.value:
            credential_ref.status = ProviderCredentialStatus.TEST_FAILED.value
        await self.session.flush()
        await self.session.refresh(connection_test)
        await self.session.refresh(credential_ref)
        await self.session.commit()
        return connection_test

    async def test_provider_configuration(
        self,
        payload: ProviderConfigurationTestRequest,
    ) -> ProviderConnectionTest:
        self.validate_public_metadata(payload.request_metadata_json)
        result = await self.connection_tester.run_test(
            CredentialConnectionTestInput(
                provider=payload.provider,
                credential_type=payload.credential_type.value,
                test_type=payload.test_type,
                secret_ref_configured=False,
                request_metadata_json=payload.request_metadata_json,
            )
        )
        connection_test = await self.record_connection_test(
            workspace_id=payload.workspace_id,
            credential_ref_id=None,
            provider=payload.provider,
            test_type=payload.test_type,
            result=result,
        )
        await self.session.commit()
        await self.session.refresh(connection_test)
        return connection_test

    async def get_connection_test(self, test_id: UUID) -> ProviderConnectionTest:
        connection_test = await self.repository.get_connection_test(test_id)
        if connection_test is None:
            raise AppError(
                404,
                "provider_connection_test_not_found",
                "Provider connection test not found",
            )
        return connection_test

    async def record_connection_test(
        self,
        workspace_id: UUID,
        credential_ref_id: UUID | None,
        provider: str,
        test_type: ProviderConnectionTestType,
        result: CredentialConnectionTestResult,
    ) -> ProviderConnectionTest:
        return await self.repository.add_connection_test(
            ProviderConnectionTest(
                workspace_id=workspace_id,
                credential_ref_id=credential_ref_id,
                provider=provider,
                test_type=test_type.value,
                status=result.status.value,
                request_metadata_json=redact_payload(result.request_metadata_json),
                response_metadata_json=redact_payload(result.response_metadata_json),
                error_message=truncate(result.error_message, 1000)
                if result.error_message is not None
                else None,
            )
        )

    def validate_public_metadata(self, value: dict[str, object]) -> None:
        sensitive_paths = find_sensitive_payload_paths(value)
        if sensitive_paths:
            raise AppError(
                422,
                "provider_credential_metadata_contains_secret",
                "Provider credential metadata must not include inline secrets",
            )

    def effective_status(
        self,
        credential_type: ProviderCredentialType,
        status: ProviderCredentialStatus,
        secret_ref: str | None,
    ) -> ProviderCredentialStatus:
        if credential_type != ProviderCredentialType.NONE_REQUIRED and not secret_ref:
            return ProviderCredentialStatus.MISSING
        return status

    def default_test_type(
        self,
        credential_ref: ProviderCredentialRef,
    ) -> ProviderConnectionTestType:
        if credential_ref.provider in {"mock", "mock_polling", "mock_live"}:
            return ProviderConnectionTestType.MOCK
        if credential_ref.credential_type == ProviderCredentialType.NONE_REQUIRED.value:
            return ProviderConnectionTestType.PUBLIC_ENDPOINT
        return ProviderConnectionTestType.AUTHENTICATED_ENDPOINT

    async def assert_credential_ref_workspace(
        self,
        credential_ref_id: UUID,
        workspace_id: UUID,
    ) -> ProviderCredentialRef:
        credential_ref = await self.get_credential_ref(credential_ref_id)
        if credential_ref.workspace_id != workspace_id:
            raise AppError(
                422,
                "provider_credential_workspace_mismatch",
                "Provider credential reference does not belong to this workspace",
            )
        return credential_ref

    def to_read_schema(self, credential_ref: ProviderCredentialRef) -> ProviderCredentialRefRead:
        payload = {
            "id": credential_ref.id,
            "workspace_id": credential_ref.workspace_id,
            "name": credential_ref.name,
            "provider": credential_ref.provider,
            "credential_type": credential_ref.credential_type,
            "status": credential_ref.status,
            "secret_ref_configured": credential_ref.secret_ref is not None,
            "secret_ref_summary": secret_ref_summary(credential_ref.secret_ref),
            "public_metadata_json": redact_payload(credential_ref.public_metadata_json),
            "last_test_status": credential_ref.last_test_status,
            "last_tested_at": credential_ref.last_tested_at,
            "last_error_message": credential_ref.last_error_message,
            "rotated_at": credential_ref.rotated_at,
            "created_at": credential_ref.created_at,
            "updated_at": credential_ref.updated_at,
        }
        return ProviderCredentialRefRead.model_validate(payload)


def secret_ref_summary(secret_ref: str | None) -> dict[str, object] | None:
    if secret_ref is None:
        return None
    prefix = secret_ref.split(":", 1)[0] if ":" in secret_ref else "reference"
    digest = hashlib.sha256(secret_ref.encode("utf-8")).hexdigest()[:12]
    return {"kind": prefix, "fingerprint": digest, "configured": True}


def truncate(value: str, max_length: int) -> str:
    return value if len(value) <= max_length else value[:max_length]
