from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.equity_data.models import (
    EquityDataImportError,
    EquityDataProviderRequest,
    EquityEarningsEvent,
    EquityFundamentalSnapshot,
    EquitySymbolMetadataSnapshot,
)


class EquityDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_provider_request(
        self,
        request: EquityDataProviderRequest,
    ) -> EquityDataProviderRequest:
        self.session.add(request)
        await self.session.flush()
        await self.session.refresh(request)
        return request

    async def update_provider_request(
        self,
        request: EquityDataProviderRequest,
    ) -> EquityDataProviderRequest:
        await self.session.flush()
        await self.session.refresh(request)
        return request

    async def get_provider_request(
        self,
        request_id: UUID,
    ) -> EquityDataProviderRequest | None:
        return await self.session.get(EquityDataProviderRequest, request_id)

    async def list_provider_requests(
        self,
        workspace_id: UUID,
        provider: str | None,
        request_type: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[EquityDataProviderRequest]:
        statement: Select[tuple[EquityDataProviderRequest]] = (
            select(EquityDataProviderRequest)
            .where(EquityDataProviderRequest.workspace_id == workspace_id)
            .order_by(EquityDataProviderRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if provider is not None:
            statement = statement.where(EquityDataProviderRequest.provider == provider)
        if request_type is not None:
            statement = statement.where(EquityDataProviderRequest.request_type == request_type)
        if status is not None:
            statement = statement.where(EquityDataProviderRequest.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def add_import_error(self, error: EquityDataImportError) -> EquityDataImportError:
        self.session.add(error)
        await self.session.flush()
        await self.session.refresh(error)
        return error

    async def list_import_errors(
        self,
        provider_request_id: UUID,
        limit: int,
        offset: int,
    ) -> list[EquityDataImportError]:
        statement = (
            select(EquityDataImportError)
            .where(EquityDataImportError.provider_request_id == provider_request_id)
            .order_by(EquityDataImportError.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_metadata_snapshot(
        self,
        snapshot: EquitySymbolMetadataSnapshot,
    ) -> EquitySymbolMetadataSnapshot:
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_latest_metadata(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
    ) -> EquitySymbolMetadataSnapshot | None:
        statement = (
            select(EquitySymbolMetadataSnapshot)
            .where(
                EquitySymbolMetadataSnapshot.workspace_id == workspace_id,
                EquitySymbolMetadataSnapshot.symbol_id == symbol_id,
            )
            .order_by(
                EquitySymbolMetadataSnapshot.snapshot_time.desc(),
                EquitySymbolMetadataSnapshot.created_at.desc(),
            )
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_fundamental_snapshot(
        self,
        snapshot: EquityFundamentalSnapshot,
    ) -> EquityFundamentalSnapshot:
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_latest_fundamentals(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
    ) -> EquityFundamentalSnapshot | None:
        statement = (
            select(EquityFundamentalSnapshot)
            .where(
                EquityFundamentalSnapshot.workspace_id == workspace_id,
                EquityFundamentalSnapshot.symbol_id == symbol_id,
            )
            .order_by(
                EquityFundamentalSnapshot.snapshot_time.desc(),
                EquityFundamentalSnapshot.created_at.desc(),
            )
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_earnings_event(self, event: EquityEarningsEvent) -> EquityEarningsEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get_earnings_event(self, event_id: UUID) -> EquityEarningsEvent | None:
        return await self.session.get(EquityEarningsEvent, event_id)

    async def list_symbol_earnings(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        limit: int,
        offset: int,
    ) -> list[EquityEarningsEvent]:
        statement = (
            select(EquityEarningsEvent)
            .where(
                EquityEarningsEvent.workspace_id == workspace_id,
                EquityEarningsEvent.symbol_id == symbol_id,
            )
            .order_by(EquityEarningsEvent.event_date.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_symbol_earnings_window(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        limit: int,
    ) -> list[EquityEarningsEvent]:
        statement = (
            select(EquityEarningsEvent)
            .where(
                EquityEarningsEvent.workspace_id == workspace_id,
                EquityEarningsEvent.symbol_id == symbol_id,
            )
            .order_by(EquityEarningsEvent.event_date.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
