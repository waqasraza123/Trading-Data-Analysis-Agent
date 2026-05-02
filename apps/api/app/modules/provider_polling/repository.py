from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.provider_polling.models import ProviderPollingError, ProviderPollingRequest


class ProviderPollingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_request(
        self,
        polling_request: ProviderPollingRequest,
    ) -> ProviderPollingRequest:
        self.session.add(polling_request)
        await self.session.flush()
        await self.session.refresh(polling_request)
        return polling_request

    async def get_request(self, request_id: UUID) -> ProviderPollingRequest | None:
        return await self.session.get(ProviderPollingRequest, request_id)

    async def list_requests(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        status: str | None = None,
        provider: str | None = None,
        symbol_id: UUID | None = None,
        source_id: UUID | None = None,
    ) -> list[ProviderPollingRequest]:
        statement: Select[tuple[ProviderPollingRequest]] = (
            select(ProviderPollingRequest)
            .order_by(ProviderPollingRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(ProviderPollingRequest.workspace_id == workspace_id)
        if status is not None:
            statement = statement.where(ProviderPollingRequest.status == status)
        if provider is not None:
            statement = statement.where(ProviderPollingRequest.provider == provider)
        if symbol_id is not None:
            statement = statement.where(ProviderPollingRequest.symbol_id == symbol_id)
        if source_id is not None:
            statement = statement.where(ProviderPollingRequest.source_id == source_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def add_error(self, error: ProviderPollingError) -> ProviderPollingError:
        self.session.add(error)
        await self.session.flush()
        await self.session.refresh(error)
        return error

    async def list_errors(
        self,
        polling_request_id: UUID,
        limit: int,
        offset: int,
    ) -> list[ProviderPollingError]:
        statement: Select[tuple[ProviderPollingError]] = (
            select(ProviderPollingError)
            .where(ProviderPollingError.polling_request_id == polling_request_id)
            .order_by(ProviderPollingError.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
