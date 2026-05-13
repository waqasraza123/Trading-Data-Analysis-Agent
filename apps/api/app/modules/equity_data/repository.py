from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.equity_data.models import (
    EquityDataImportError,
    EquityDataOperation,
    EquityDataProviderRequest,
    EquityEarningsEvent,
    EquityFundamentalSnapshot,
    EquitySymbolMetadataSnapshot,
)
from app.modules.equity_research.models import EquityCatalystContext, EquityUniverseMember


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

    async def create_operation(self, operation: EquityDataOperation) -> EquityDataOperation:
        self.session.add(operation)
        await self.session.flush()
        await self.session.refresh(operation)
        return operation

    async def update_operation(self, operation: EquityDataOperation) -> EquityDataOperation:
        await self.session.flush()
        await self.session.refresh(operation)
        return operation

    async def get_operation(self, operation_id: UUID) -> EquityDataOperation | None:
        return await self.session.get(EquityDataOperation, operation_id)

    async def get_operation_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str,
    ) -> EquityDataOperation | None:
        statement: Select[tuple[EquityDataOperation]] = (
            select(EquityDataOperation)
            .where(
                EquityDataOperation.workspace_id == workspace_id,
                EquityDataOperation.idempotency_key == idempotency_key,
            )
            .order_by(EquityDataOperation.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_operations(
        self,
        workspace_id: UUID,
        status: str | None,
        operation_type: str | None,
        provider_name: str | None,
        limit: int,
        offset: int,
    ) -> list[EquityDataOperation]:
        statement: Select[tuple[EquityDataOperation]] = (
            select(EquityDataOperation)
            .where(EquityDataOperation.workspace_id == workspace_id)
            .order_by(EquityDataOperation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(EquityDataOperation.status == status)
        if operation_type is not None:
            statement = statement.where(EquityDataOperation.operation_type == operation_type)
        if provider_name is not None:
            statement = statement.where(EquityDataOperation.provider_name == provider_name)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_operations_by_status(self, workspace_id: UUID) -> dict[str, int]:
        statement = (
            select(EquityDataOperation.status, func.count())
            .where(EquityDataOperation.workspace_id == workspace_id)
            .group_by(EquityDataOperation.status)
        )
        result = await self.session.execute(statement)
        return {str(status): int(count) for status, count in result.all()}

    async def count_operations_by_type(self, workspace_id: UUID) -> dict[str, int]:
        statement = (
            select(EquityDataOperation.operation_type, func.count())
            .where(EquityDataOperation.workspace_id == workspace_id)
            .group_by(EquityDataOperation.operation_type)
        )
        result = await self.session.execute(statement)
        return {str(operation_type): int(count) for operation_type, count in result.all()}

    async def count_operations_by_provider(self, workspace_id: UUID) -> dict[str, int]:
        statement = (
            select(EquityDataOperation.provider_name, func.count())
            .where(EquityDataOperation.workspace_id == workspace_id)
            .group_by(EquityDataOperation.provider_name)
        )
        result = await self.session.execute(statement)
        return {
            str(provider_name or "internal"): int(count)
            for provider_name, count in result.all()
        }

    async def get_latest_operation_timestamp(self, workspace_id: UUID) -> datetime | None:
        statement = select(func.max(EquityDataOperation.created_at)).where(
            EquityDataOperation.workspace_id == workspace_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_recent_problem_operations(
        self,
        workspace_id: UUID,
        limit: int,
    ) -> list[EquityDataOperation]:
        statement = (
            select(EquityDataOperation)
            .where(
                EquityDataOperation.workspace_id == workspace_id,
                EquityDataOperation.status.in_(
                    ["completed_with_warnings", "failed", "cancelled"]
                ),
            )
            .order_by(EquityDataOperation.updated_at.desc())
            .limit(limit)
        )
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

    async def list_universe_symbol_ids(
        self,
        workspace_id: UUID,
        universe_id: UUID,
        limit: int,
    ) -> list[UUID]:
        statement = (
            select(EquityUniverseMember.symbol_id)
            .where(
                EquityUniverseMember.workspace_id == workspace_id,
                EquityUniverseMember.universe_id == universe_id,
                EquityUniverseMember.is_active.is_(True),
            )
            .order_by(EquityUniverseMember.ticker.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_earnings_events_for_symbols(
        self,
        workspace_id: UUID,
        symbol_ids: list[UUID],
        limit: int,
    ) -> list[EquityEarningsEvent]:
        if not symbol_ids:
            return []
        statement = (
            select(EquityEarningsEvent)
            .where(
                EquityEarningsEvent.workspace_id == workspace_id,
                EquityEarningsEvent.symbol_id.in_(symbol_ids),
            )
            .order_by(EquityEarningsEvent.event_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_catalyst_for_earnings_event(
        self,
        workspace_id: UUID,
        earnings_event_id: UUID,
    ) -> EquityCatalystContext | None:
        statement = (
            select(EquityCatalystContext)
            .where(
                EquityCatalystContext.workspace_id == workspace_id,
                EquityCatalystContext.raw_reference_json["equityEarningsEventId"].astext
                == str(earnings_event_id),
            )
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
