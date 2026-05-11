from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.equity_data.adapters import EQUITY_DATA_PROVIDERS, get_equity_data_provider
from app.modules.equity_data.adapters.base import (
    EquityEarningsItem,
    EquityFundamentalsItem,
    EquityMetadataItem,
    EquityProviderContext,
    EquityProviderResult,
)
from app.modules.equity_data.credentials import EquityCredentialResolver
from app.modules.equity_data.models import (
    EquityDataImportError,
    EquityDataProviderRequest,
    EquityDataRequestStatus,
    EquityDataRequestType,
    EquityEarningsEvent,
    EquityEarningsImportance,
    EquityEarningsStatus,
    EquityFundamentalSnapshot,
    EquitySymbolMetadataSnapshot,
)
from app.modules.equity_data.normalizer import (
    event_datetime,
    normalize_provider,
    normalize_ticker,
    safe_reference,
)
from app.modules.equity_data.repository import EquityDataRepository
from app.modules.equity_data.schemas import (
    EquityDataProviderCapability,
    EquityEarningsImportRowsRequest,
    EquityProviderUniverseImportRequest,
    EquitySymbolProviderRequest,
    EquityUniverseImportRowsRequest,
)
from app.modules.equity_research.models import (
    EquityCatalystContext,
    EquityCatalystSentiment,
    EquityCatalystType,
    EquityUniverse,
    EquityUniverseMember,
    EquityUniverseStatus,
    EquityUniverseType,
)
from app.modules.equity_research.repository import EquityResearchRepository
from app.modules.provider_credentials.models import ProviderCredentialStatus
from app.modules.provider_credentials.repository import ProviderCredentialRepository
from app.modules.symbols.models import MarketType, Symbol
from app.modules.symbols.repository import SymbolRepository
from app.modules.workspaces.repository import WorkspaceRepository


class EquityDataService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: EquityDataRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or EquityDataRepository(session)
        self.equity_repository = EquityResearchRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.workspace_repository = WorkspaceRepository(session)
        self.credential_repository = ProviderCredentialRepository(session)
        self.credential_resolver = EquityCredentialResolver(session, self.settings)

    async def list_providers(self) -> list[EquityDataProviderCapability]:
        capabilities: list[EquityDataProviderCapability] = []
        for provider in EQUITY_DATA_PROVIDERS.values():
            external = provider.key() not in {"mock_equity_data", "csv_equity_import"}
            configured = (
                self.settings.equity_data_enable_mock_provider
                if provider.key() == "mock_equity_data"
                else not external or self.settings.equity_data_allow_external_requests
            )
            if (
                provider.requires_credential_ref()
                and not self.settings.equity_data_allow_external_requests
            ):
                status = EquityDataRequestStatus.PROVIDER_NOT_CONFIGURED
                message = "External provider requests are disabled"
            elif provider.key() == "generic_http":
                status = EquityDataRequestStatus.PROVIDER_NOT_CONFIGURED
                message = "Generic HTTP provider requires explicit server configuration"
            else:
                status = (
                    EquityDataRequestStatus.COMPLETED
                    if configured
                    else EquityDataRequestStatus.PROVIDER_NOT_CONFIGURED
                )
                message = "Provider configured" if configured else "Provider not configured"
            capabilities.append(
                EquityDataProviderCapability(
                    provider=provider.key(),
                    label=provider.label(),
                    configured=configured,
                    external_requests_enabled=self.settings.equity_data_allow_external_requests,
                    requires_credential_ref=provider.requires_credential_ref(),
                    supports_universe_import=provider.supports_universe_import(),
                    supports_metadata_lookup=provider.supports_metadata_lookup(),
                    supports_fundamentals_snapshot=provider.supports_fundamentals_snapshot(),
                    supports_earnings_calendar=provider.supports_earnings_calendar(),
                    status=status,
                    message=message,
                )
            )
        return capabilities

    async def test_provider(
        self,
        workspace_id: UUID,
        provider_key: str,
        credential_ref_id: UUID | None,
    ) -> tuple[EquityDataRequestStatus, str, bool]:
        await self.validate_workspace(workspace_id)
        provider = get_equity_data_provider(provider_key)
        credential_configured = await self.validate_provider_access(
            workspace_id,
            provider.key(),
            credential_ref_id,
            provider.requires_credential_ref(),
        )
        if provider.key() == "generic_http":
            return (
                EquityDataRequestStatus.PROVIDER_NOT_CONFIGURED,
                "Provider not configured",
                False,
            )
        if provider.requires_credential_ref() and not credential_configured:
            return (
                EquityDataRequestStatus.PROVIDER_NOT_CONFIGURED,
                "Credential reference is required",
                False,
            )
        if provider.requires_credential_ref():
            resolution = await self.credential_resolver.resolve_credential_ref(
                provider.key(),
                credential_ref_id,
                workspace_id,
            )
            if not resolution.ready:
                return (EquityDataRequestStatus.PROVIDER_NOT_CONFIGURED, resolution.message, False)
            return (
                EquityDataRequestStatus.COMPLETED,
                "Provider credential material is available for read-only data requests",
                True,
            )
        return (EquityDataRequestStatus.COMPLETED, "Provider configured", True)

    async def import_universe_from_rows(
        self,
        payload: EquityUniverseImportRowsRequest,
    ) -> EquityDataProviderRequest:
        await self.validate_workspace(payload.workspace_id)
        provider = get_equity_data_provider(payload.provider)
        if len(payload.rows) > self.settings.equity_data_max_universe_import_rows:
            raise AppError(
                422, "equity_data_import_too_large", "Universe import row limit exceeded"
            )
        request = await self.create_request(
            workspace_id=payload.workspace_id,
            provider=provider.key(),
            request_type=EquityDataRequestType.UNIVERSE_IMPORT,
            credential_ref_id=None,
            universe_id=payload.universe_id,
            symbol_id=None,
            ticker=None,
            request_json=payload.model_dump(mode="json", by_alias=True),
        )
        await self.session.commit()
        rows = [row.model_dump(mode="python", by_alias=True) for row in payload.rows]
        result = await provider.import_universe(
            await self.provider_context(payload.workspace_id, provider.key(), None),
            {"rows": rows},
        )
        return await self.store_universe_import_result(
            request,
            result,
            universe_id=payload.universe_id,
            create_universe_name=payload.create_universe_name,
        )

    async def import_universe_from_provider(
        self,
        payload: EquityProviderUniverseImportRequest,
    ) -> EquityDataProviderRequest:
        await self.validate_workspace(payload.workspace_id)
        provider = get_equity_data_provider(payload.provider)
        await self.validate_provider_access(
            payload.workspace_id,
            provider.key(),
            payload.credential_ref_id,
            provider.requires_credential_ref(),
        )
        request = await self.create_request(
            workspace_id=payload.workspace_id,
            provider=provider.key(),
            request_type=EquityDataRequestType.UNIVERSE_IMPORT,
            credential_ref_id=payload.credential_ref_id,
            universe_id=payload.universe_id,
            symbol_id=None,
            ticker=None,
            request_json=payload.model_dump(mode="json", by_alias=True),
        )
        await self.session.commit()
        result = await provider.import_universe(
            await self.provider_context(
                payload.workspace_id,
                provider.key(),
                payload.credential_ref_id,
            ),
            payload.model_dump(mode="python", by_alias=True),
        )
        return await self.store_universe_import_result(
            request,
            result,
            universe_id=payload.universe_id,
            create_universe_name=payload.create_universe_name,
        )

    async def lookup_and_store_metadata(
        self,
        symbol_id: UUID,
        payload: EquitySymbolProviderRequest,
    ) -> EquityDataProviderRequest:
        symbol = await self.validate_stock_symbol(symbol_id)
        provider_key = payload.provider or self.settings.equity_data_default_provider
        provider = get_equity_data_provider(provider_key)
        await self.validate_provider_access(
            payload.workspace_id,
            provider.key(),
            payload.credential_ref_id,
            provider.requires_credential_ref(),
        )
        request = await self.create_request(
            workspace_id=payload.workspace_id,
            provider=provider.key(),
            request_type=EquityDataRequestType.SYMBOL_METADATA_LOOKUP,
            credential_ref_id=payload.credential_ref_id,
            universe_id=None,
            symbol_id=symbol.id,
            ticker=symbol.symbol,
            request_json=payload.model_dump(mode="json", by_alias=True),
        )
        await self.session.commit()
        result = await provider.lookup_symbol_metadata(
            await self.provider_context(
                payload.workspace_id,
                provider.key(),
                payload.credential_ref_id,
            ),
            {"ticker": symbol.symbol, "filters": payload.filters},
        )
        return await self.store_metadata_result(request, result, {symbol.symbol: symbol})

    async def fetch_and_store_fundamentals(
        self,
        symbol_id: UUID,
        payload: EquitySymbolProviderRequest,
    ) -> EquityDataProviderRequest:
        symbol = await self.validate_stock_symbol(symbol_id)
        provider_key = payload.provider or self.settings.equity_data_default_provider
        provider = get_equity_data_provider(provider_key)
        await self.validate_provider_access(
            payload.workspace_id,
            provider.key(),
            payload.credential_ref_id,
            provider.requires_credential_ref(),
        )
        request = await self.create_request(
            workspace_id=payload.workspace_id,
            provider=provider.key(),
            request_type=EquityDataRequestType.FUNDAMENTALS_SNAPSHOT,
            credential_ref_id=payload.credential_ref_id,
            universe_id=None,
            symbol_id=symbol.id,
            ticker=symbol.symbol,
            request_json=payload.model_dump(mode="json", by_alias=True),
        )
        await self.session.commit()
        result = await provider.fetch_fundamentals_snapshot(
            await self.provider_context(
                payload.workspace_id,
                provider.key(),
                payload.credential_ref_id,
            ),
            {"ticker": symbol.symbol, "filters": payload.filters},
        )
        return await self.store_fundamentals_result(request, result, {symbol.symbol: symbol})

    async def fetch_and_store_earnings(
        self,
        symbol_id: UUID,
        payload: EquitySymbolProviderRequest,
    ) -> EquityDataProviderRequest:
        symbol = await self.validate_stock_symbol(symbol_id)
        provider_key = payload.provider or self.settings.equity_data_default_provider
        provider = get_equity_data_provider(provider_key)
        await self.validate_provider_access(
            payload.workspace_id,
            provider.key(),
            payload.credential_ref_id,
            provider.requires_credential_ref(),
        )
        request = await self.create_request(
            workspace_id=payload.workspace_id,
            provider=provider.key(),
            request_type=EquityDataRequestType.EARNINGS_CALENDAR,
            credential_ref_id=payload.credential_ref_id,
            universe_id=None,
            symbol_id=symbol.id,
            ticker=symbol.symbol,
            request_json=payload.model_dump(mode="json", by_alias=True),
        )
        await self.session.commit()
        result = await provider.fetch_earnings_events(
            await self.provider_context(
                payload.workspace_id,
                provider.key(),
                payload.credential_ref_id,
            ),
            {"ticker": symbol.symbol, "filters": payload.filters},
        )
        return await self.store_earnings_result(request, result, {symbol.symbol: symbol})

    async def import_earnings_rows(
        self,
        payload: EquityEarningsImportRowsRequest,
    ) -> EquityDataProviderRequest:
        await self.validate_workspace(payload.workspace_id)
        if len(payload.rows) > self.settings.equity_data_max_universe_import_rows:
            raise AppError(
                422, "equity_data_import_too_large", "Earnings import row limit exceeded"
            )
        request = await self.create_request(
            workspace_id=payload.workspace_id,
            provider=payload.provider,
            request_type=EquityDataRequestType.EARNINGS_CALENDAR,
            credential_ref_id=None,
            universe_id=None,
            symbol_id=None,
            ticker=None,
            request_json=payload.model_dump(mode="json", by_alias=True),
        )
        await self.session.commit()
        symbols: dict[str, Symbol] = {}
        earnings: list[EquityEarningsItem] = []
        for index, row in enumerate(payload.rows, start=1):
            try:
                symbol = await self.symbol_from_earnings_row(row.symbol_id, row.ticker)
                symbols[symbol.symbol] = symbol
                earnings.append(
                    EquityEarningsItem(
                        ticker=symbol.symbol,
                        event_date=row.event_date,
                        fiscal_period=row.fiscal_period,
                        report_time=row.report_time,
                        eps_estimate=row.eps_estimate,
                        eps_actual=row.eps_actual,
                        revenue_estimate=row.revenue_estimate,
                        revenue_actual=row.revenue_actual,
                        importance=row.importance.value,
                        status=row.status.value,
                        raw_reference_json=safe_reference(row.raw_reference_json),
                    )
                )
            except Exception as error:
                await self.record_import_error(
                    request, index, error, row.model_dump(mode="json", by_alias=True)
                )
        result = EquityProviderResult(
            status="completed",
            earnings=earnings,
            summary={
                "provider": payload.provider,
                "received": len(payload.rows),
                "count": len(earnings),
            },
        )
        return await self.store_earnings_result(request, result, symbols)

    async def convert_earnings_to_catalyst_context(
        self,
        event_id: UUID,
    ) -> EquityCatalystContext:
        event = await self.repository.get_earnings_event(event_id)
        if event is None:
            raise AppError(404, "equity_earnings_event_not_found", "Earnings event not found")
        symbol = await self.validate_stock_symbol(event.symbol_id)
        title = f"{symbol.symbol} earnings context"
        summary = earnings_catalyst_summary(symbol.symbol, event)
        catalyst = EquityCatalystContext(
            workspace_id=event.workspace_id,
            symbol_id=event.symbol_id,
            source_type=f"equity_data:{event.provider}",
            event_time=event_datetime(event.event_date, event.report_time),
            catalyst_type=EquityCatalystType.EARNINGS.value,
            title=title,
            summary=summary,
            importance=event.importance,
            sentiment=EquityCatalystSentiment.UNKNOWN.value,
            raw_reference_json=safe_reference(
                {
                    "equityEarningsEventId": str(event.id),
                    "provider": event.provider,
                    "status": event.status,
                }
            ),
        )
        created = await self.equity_repository.create_catalyst(catalyst)
        await self.session.commit()
        return created

    async def get_symbol_latest_metadata(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
    ) -> EquitySymbolMetadataSnapshot | None:
        await self.validate_workspace(workspace_id)
        await self.validate_stock_symbol(symbol_id)
        return await self.repository.get_latest_metadata(workspace_id, symbol_id)

    async def get_symbol_latest_fundamentals(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
    ) -> EquityFundamentalSnapshot | None:
        await self.validate_workspace(workspace_id)
        await self.validate_stock_symbol(symbol_id)
        return await self.repository.get_latest_fundamentals(workspace_id, symbol_id)

    async def list_symbol_earnings(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        limit: int,
        offset: int,
    ) -> list[EquityEarningsEvent]:
        await self.validate_workspace(workspace_id)
        await self.validate_stock_symbol(symbol_id)
        return await self.repository.list_symbol_earnings(workspace_id, symbol_id, limit, offset)

    async def list_provider_requests(
        self,
        workspace_id: UUID,
        provider: str | None,
        request_type: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[EquityDataProviderRequest]:
        await self.validate_workspace(workspace_id)
        return await self.repository.list_provider_requests(
            workspace_id,
            normalize_provider(provider) if provider else None,
            request_type,
            status,
            limit,
            offset,
        )

    async def get_provider_request(self, request_id: UUID) -> EquityDataProviderRequest:
        request = await self.repository.get_provider_request(request_id)
        if request is None:
            raise AppError(
                404, "equity_data_provider_request_not_found", "Provider request not found"
            )
        return request

    async def list_request_errors(
        self,
        request_id: UUID,
        limit: int,
        offset: int,
    ) -> list[EquityDataImportError]:
        await self.get_provider_request(request_id)
        return await self.repository.list_import_errors(request_id, limit, offset)

    async def store_universe_import_result(
        self,
        request: EquityDataProviderRequest,
        result: EquityProviderResult,
        universe_id: UUID | None,
        create_universe_name: str | None,
    ) -> EquityDataProviderRequest:
        request.status = EquityDataRequestStatus.RUNNING.value
        request.started_at = datetime.now(UTC)
        await self.repository.update_provider_request(request)
        universe = await self.resolve_universe(
            request.workspace_id, universe_id, create_universe_name
        )
        symbols: dict[str, Symbol] = {}
        stored = 0
        skipped = 0
        for index, item in enumerate(result.metadata, start=1):
            try:
                symbol = await self.create_or_update_equity_symbol(item)
                symbols[item.ticker] = symbol
                await self.attach_symbol_to_universe(universe, symbol, item)
                await self.store_metadata_snapshot(
                    request.workspace_id, request.provider, symbol, item
                )
                stored += 1
            except Exception as error:
                skipped += 1
                await self.record_import_error(
                    request, index, error, item.raw_reference_json or {"ticker": item.ticker}
                )
        request.universe_id = universe.id
        request.received_count = len(result.metadata)
        request.stored_count = stored
        request.skipped_count = skipped
        request.failed_count = skipped
        return await self.finish_request(request, result)

    async def store_metadata_result(
        self,
        request: EquityDataProviderRequest,
        result: EquityProviderResult,
        symbols: dict[str, Symbol],
    ) -> EquityDataProviderRequest:
        request.status = EquityDataRequestStatus.RUNNING.value
        request.started_at = datetime.now(UTC)
        stored = 0
        skipped = 0
        for index, item in enumerate(result.metadata, start=1):
            try:
                symbol = symbols.get(item.ticker) or await self.create_or_update_equity_symbol(item)
                await self.store_metadata_snapshot(
                    request.workspace_id, request.provider, symbol, item
                )
                stored += 1
            except Exception as error:
                skipped += 1
                await self.record_import_error(
                    request, index, error, item.raw_reference_json or {"ticker": item.ticker}
                )
        request.received_count = len(result.metadata)
        request.stored_count = stored
        request.skipped_count = skipped
        request.failed_count = skipped
        return await self.finish_request(request, result)

    async def store_fundamentals_result(
        self,
        request: EquityDataProviderRequest,
        result: EquityProviderResult,
        symbols: dict[str, Symbol],
    ) -> EquityDataProviderRequest:
        request.status = EquityDataRequestStatus.RUNNING.value
        request.started_at = datetime.now(UTC)
        stored = 0
        skipped = 0
        for index, item in enumerate(result.fundamentals, start=1):
            try:
                symbol = symbols.get(item.ticker)
                if symbol is None:
                    symbol = await self.validate_stock_symbol_by_ticker(item.ticker)
                await self.store_fundamental_snapshot(
                    request.workspace_id, request.provider, symbol, item
                )
                stored += 1
            except Exception as error:
                skipped += 1
                await self.record_import_error(
                    request, index, error, item.raw_reference_json or {"ticker": item.ticker}
                )
        request.received_count = len(result.fundamentals)
        request.stored_count = stored
        request.skipped_count = skipped
        request.failed_count = skipped
        return await self.finish_request(request, result)

    async def store_earnings_result(
        self,
        request: EquityDataProviderRequest,
        result: EquityProviderResult,
        symbols: dict[str, Symbol],
    ) -> EquityDataProviderRequest:
        request.status = EquityDataRequestStatus.RUNNING.value
        request.started_at = datetime.now(UTC)
        stored = 0
        skipped = 0
        for index, item in enumerate(result.earnings, start=1):
            try:
                symbol = symbols.get(item.ticker)
                if symbol is None:
                    symbol = await self.validate_stock_symbol_by_ticker(item.ticker)
                await self.store_earnings_event(
                    request.workspace_id, request.provider, symbol, item
                )
                stored += 1
            except Exception as error:
                skipped += 1
                await self.record_import_error(
                    request, index, error, item.raw_reference_json or {"ticker": item.ticker}
                )
        request.received_count = len(result.earnings)
        request.stored_count = stored
        request.skipped_count = skipped
        request.failed_count = skipped
        return await self.finish_request(request, result)

    async def finish_request(
        self,
        request: EquityDataProviderRequest,
        result: EquityProviderResult,
    ) -> EquityDataProviderRequest:
        if result.status in {
            EquityDataRequestStatus.PROVIDER_NOT_CONFIGURED.value,
            EquityDataRequestStatus.PROVIDER_NOT_IMPLEMENTED.value,
            EquityDataRequestStatus.FAILED.value,
        }:
            request.status = result.status
        elif request.failed_count > 0:
            request.status = EquityDataRequestStatus.COMPLETED_WITH_WARNINGS.value
        else:
            request.status = EquityDataRequestStatus.COMPLETED.value
        request.response_summary_json = safe_reference(
            result.summary | {"warnings": result.warnings}
        )
        request.error_message = truncate(result.error_message, 1000)
        request.completed_at = datetime.now(UTC)
        try:
            await self.repository.update_provider_request(request)
            await self.session.commit()
            return request
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409, "equity_data_request_conflict", "Equity data request could not be stored"
            ) from error

    async def create_request(
        self,
        workspace_id: UUID,
        provider: str,
        request_type: EquityDataRequestType,
        credential_ref_id: UUID | None,
        universe_id: UUID | None,
        symbol_id: UUID | None,
        ticker: str | None,
        request_json: dict[str, object],
    ) -> EquityDataProviderRequest:
        return await self.repository.create_provider_request(
            EquityDataProviderRequest(
                workspace_id=workspace_id,
                provider=provider,
                request_type=request_type.value,
                status=EquityDataRequestStatus.PENDING.value,
                credential_ref_id=credential_ref_id,
                universe_id=universe_id,
                symbol_id=symbol_id,
                ticker=ticker,
                request_json=safe_reference(request_json),
                response_summary_json={},
            )
        )

    async def resolve_universe(
        self,
        workspace_id: UUID,
        universe_id: UUID | None,
        create_universe_name: str | None,
    ) -> EquityUniverse:
        if universe_id is not None:
            universe = await self.equity_repository.get_universe(universe_id)
            if universe is None:
                raise AppError(404, "equity_universe_not_found", "Equity universe not found")
            if universe.workspace_id != workspace_id:
                raise AppError(
                    422,
                    "equity_universe_workspace_mismatch",
                    "Universe does not belong to workspace",
                )
            return universe
        if create_universe_name is None:
            raise AppError(
                422, "equity_universe_required", "Universe id or create universe name is required"
            )
        universe = EquityUniverse(
            workspace_id=workspace_id,
            name=create_universe_name,
            description="Imported stock universe",
            status=EquityUniverseStatus.ACTIVE.value,
            universe_type=EquityUniverseType.CUSTOM.value,
            filters_json={},
            metadata_json={"source": "equity_data_import"},
        )
        return await self.equity_repository.create_universe(universe)

    async def create_or_update_equity_symbol(self, item: EquityMetadataItem) -> Symbol:
        ticker = normalize_ticker(item.ticker)
        existing = await self.symbol_repository.get_by_symbol(ticker)
        if existing is not None:
            if existing.market_type != MarketType.STOCK.value:
                raise AppError(
                    422, "equity_data_symbol_conflict", "Ticker exists with a non-stock market type"
                )
            if item.company_name and existing.display_name == existing.symbol:
                existing.display_name = item.company_name
            if not existing.is_active and item.is_active:
                existing.is_active = True
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        symbol = Symbol(
            symbol=ticker,
            display_name=item.company_name or ticker,
            market_type=MarketType.STOCK.value,
            base_asset=ticker,
            quote_asset=item.currency or "USD",
            pip_size=None,
            tick_size=Decimal("0.01"),
            price_precision=2,
            quantity_precision=0,
            is_active=item.is_active,
        )
        return await self.symbol_repository.create(symbol)

    async def attach_symbol_to_universe(
        self,
        universe: EquityUniverse,
        symbol: Symbol,
        item: EquityMetadataItem,
    ) -> EquityUniverseMember:
        existing = await self.equity_repository.get_member_by_universe_symbol(
            universe.id, symbol.id
        )
        if existing is not None:
            existing.is_active = True
            existing.ticker = item.ticker
            existing.company_name = item.company_name or symbol.display_name
            existing.sector = item.sector
            existing.industry = item.industry
            existing.exchange = item.exchange
            existing.market_cap = item.market_cap
            existing.average_volume = item.average_volume
            existing.metadata_json = safe_reference(item.raw_reference_json)
            return await self.equity_repository.update_member(existing)
        member = EquityUniverseMember(
            workspace_id=universe.workspace_id,
            universe_id=universe.id,
            symbol_id=symbol.id,
            ticker=item.ticker,
            company_name=item.company_name or symbol.display_name,
            sector=item.sector,
            industry=item.industry,
            exchange=item.exchange,
            market_cap=item.market_cap,
            average_volume=item.average_volume,
            is_active=True,
            metadata_json=safe_reference(item.raw_reference_json),
        )
        return await self.equity_repository.create_member(member)

    async def store_metadata_snapshot(
        self,
        workspace_id: UUID,
        provider: str,
        symbol: Symbol,
        item: EquityMetadataItem,
    ) -> EquitySymbolMetadataSnapshot:
        snapshot = EquitySymbolMetadataSnapshot(
            workspace_id=workspace_id,
            symbol_id=symbol.id,
            ticker=item.ticker,
            provider=provider,
            company_name=item.company_name,
            exchange=item.exchange,
            sector=item.sector,
            industry=item.industry,
            country=item.country,
            currency=item.currency,
            market_cap=item.market_cap,
            average_volume=item.average_volume,
            shares_float=item.shares_float,
            is_etf=item.is_etf,
            is_active=item.is_active,
            snapshot_time=datetime.now(UTC),
            raw_reference_json=safe_reference(item.raw_reference_json),
        )
        return await self.repository.create_metadata_snapshot(snapshot)

    async def store_fundamental_snapshot(
        self,
        workspace_id: UUID,
        provider: str,
        symbol: Symbol,
        item: EquityFundamentalsItem,
    ) -> EquityFundamentalSnapshot:
        snapshot = EquityFundamentalSnapshot(
            workspace_id=workspace_id,
            symbol_id=symbol.id,
            provider=provider,
            snapshot_time=item.snapshot_time,
            market_cap=item.market_cap,
            average_volume=item.average_volume,
            relative_volume=item.relative_volume,
            beta=item.beta,
            pe_ratio=item.pe_ratio,
            eps=item.eps,
            revenue_growth=item.revenue_growth,
            earnings_growth=item.earnings_growth,
            debt_to_equity=item.debt_to_equity,
            free_cash_flow=item.free_cash_flow,
            raw_reference_json=safe_reference(item.raw_reference_json),
        )
        return await self.repository.create_fundamental_snapshot(snapshot)

    async def store_earnings_event(
        self,
        workspace_id: UUID,
        provider: str,
        symbol: Symbol,
        item: EquityEarningsItem,
    ) -> EquityEarningsEvent:
        importance = (
            item.importance
            if item.importance in {entry.value for entry in EquityEarningsImportance}
            else EquityEarningsImportance.UNKNOWN.value
        )
        status = (
            item.status
            if item.status in {entry.value for entry in EquityEarningsStatus}
            else EquityEarningsStatus.UNKNOWN.value
        )
        event = EquityEarningsEvent(
            workspace_id=workspace_id,
            symbol_id=symbol.id,
            provider=provider,
            event_date=item.event_date,
            fiscal_period=item.fiscal_period,
            report_time=item.report_time,
            eps_estimate=item.eps_estimate,
            eps_actual=item.eps_actual,
            revenue_estimate=item.revenue_estimate,
            revenue_actual=item.revenue_actual,
            importance=importance,
            status=status,
            raw_reference_json=safe_reference(item.raw_reference_json),
        )
        return await self.repository.create_earnings_event(event)

    async def record_import_error(
        self,
        request: EquityDataProviderRequest,
        row_number: int | None,
        error: Exception,
        raw_item: object,
    ) -> None:
        code = error.code if isinstance(error, AppError) else "equity_data_item_error"
        message = (
            error.message if isinstance(error, AppError) else str(error) or type(error).__name__
        )
        await self.repository.add_import_error(
            EquityDataImportError(
                workspace_id=request.workspace_id,
                provider_request_id=request.id,
                row_number=row_number,
                error_code=truncate(code, 80) or "equity_data_item_error",
                error_message=truncate(message, 1000) or "Equity data item could not be imported",
                raw_item_json=safe_reference(raw_item),
            )
        )

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")

    async def validate_stock_symbol(self, symbol_id: UUID) -> Symbol:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if symbol.market_type != MarketType.STOCK.value:
            raise AppError(422, "equity_symbol_required", "Equity data requires stock symbols")
        return symbol

    async def validate_stock_symbol_by_ticker(self, ticker: str) -> Symbol:
        symbol = await self.symbol_repository.get_by_symbol(normalize_ticker(ticker))
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if symbol.market_type != MarketType.STOCK.value:
            raise AppError(422, "equity_symbol_required", "Equity data requires stock symbols")
        return symbol

    async def symbol_from_earnings_row(
        self,
        symbol_id: UUID | None,
        ticker: str | None,
    ) -> Symbol:
        if symbol_id is not None:
            return await self.validate_stock_symbol(symbol_id)
        if ticker is None:
            raise AppError(422, "equity_data_symbol_required", "Symbol id or ticker is required")
        return await self.validate_stock_symbol_by_ticker(ticker)

    async def validate_provider_access(
        self,
        workspace_id: UUID,
        provider: str,
        credential_ref_id: UUID | None,
        requires_credential_ref: bool,
    ) -> bool:
        if provider == "mock_equity_data":
            if not self.settings.equity_data_enable_mock_provider:
                raise AppError(
                    422, "equity_data_mock_provider_disabled", "Mock provider is disabled"
                )
            return False
        if provider == "csv_equity_import":
            return False
        if not self.settings.equity_data_allow_external_requests and (
            credential_ref_id is None or requires_credential_ref
        ):
            return False
        if requires_credential_ref and credential_ref_id is None:
            return False
        if credential_ref_id is None:
            return False
        credential = await self.credential_repository.get_credential_ref(credential_ref_id)
        if credential is None:
            raise AppError(
                404, "provider_credential_ref_not_found", "Provider credential reference not found"
            )
        if credential.workspace_id != workspace_id:
            raise AppError(
                422,
                "provider_credential_workspace_mismatch",
                "Provider credential reference does not belong to this workspace",
            )
        if credential.provider != provider:
            raise AppError(
                422,
                "provider_credential_provider_mismatch",
                "Provider credential reference is for a different provider",
            )
        if credential.status != ProviderCredentialStatus.ACTIVE.value:
            raise AppError(
                422, "provider_credential_inactive", "Provider credential reference is not active"
            )
        return True

    async def provider_context(
        self,
        workspace_id: UUID,
        provider: str,
        credential_ref_id: UUID | None,
    ) -> EquityProviderContext:
        resolution = await self.credential_resolver.resolve_credential_ref(
            provider,
            credential_ref_id,
            workspace_id,
        )
        return EquityProviderContext(
            workspace_id=str(workspace_id),
            credential_ref_id=str(credential_ref_id) if credential_ref_id is not None else None,
            external_requests_enabled=self.settings.equity_data_allow_external_requests,
            timeout_seconds=self.settings.equity_data_provider_timeout_seconds,
            retry_attempts=self.settings.equity_data_provider_retry_attempts,
            retry_backoff_seconds=self.settings.equity_data_provider_retry_backoff_seconds,
            max_pages=self.settings.equity_data_provider_max_pages,
            base_url=self.provider_base_url(provider),
            credential_secrets=resolution.secret_values if resolution.ready else {},
        )

    def provider_base_url(self, provider: str) -> str | None:
        if provider == "polygon":
            return self.settings.polygon_rest_base_url
        if provider == "alpaca":
            return self.settings.alpaca_trading_base_url
        return None


def truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length]


def earnings_catalyst_summary(ticker: str, event: EquityEarningsEvent) -> str:
    status = event.status.replace("_", " ")
    fiscal = f" for {event.fiscal_period}" if event.fiscal_period else ""
    return (
        f"{ticker} has {status} earnings context{fiscal} on {event.event_date.isoformat()}. "
        "This is catalyst context for deterministic research review and does not infer causation."
    )
