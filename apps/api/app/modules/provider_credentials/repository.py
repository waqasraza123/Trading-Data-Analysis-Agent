from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider_credentials.models import ProviderConnectionTest, ProviderCredentialRef


class ProviderCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_credential_ref(
        self,
        credential_ref: ProviderCredentialRef,
    ) -> ProviderCredentialRef:
        self.session.add(credential_ref)
        await self.session.flush()
        await self.session.refresh(credential_ref)
        return credential_ref

    async def get_credential_ref(self, credential_ref_id: UUID) -> ProviderCredentialRef | None:
        return await self.session.get(ProviderCredentialRef, credential_ref_id)

    async def list_credential_refs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        provider: str | None = None,
        status: str | None = None,
        credential_type: str | None = None,
    ) -> list[ProviderCredentialRef]:
        statement: Select[tuple[ProviderCredentialRef]] = (
            select(ProviderCredentialRef)
            .order_by(ProviderCredentialRef.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(ProviderCredentialRef.workspace_id == workspace_id)
        if provider is not None:
            statement = statement.where(ProviderCredentialRef.provider == provider)
        if status is not None:
            statement = statement.where(ProviderCredentialRef.status == status)
        if credential_type is not None:
            statement = statement.where(ProviderCredentialRef.credential_type == credential_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def add_connection_test(
        self,
        connection_test: ProviderConnectionTest,
    ) -> ProviderConnectionTest:
        self.session.add(connection_test)
        await self.session.flush()
        await self.session.refresh(connection_test)
        return connection_test

    async def get_connection_test(self, test_id: UUID) -> ProviderConnectionTest | None:
        return await self.session.get(ProviderConnectionTest, test_id)
