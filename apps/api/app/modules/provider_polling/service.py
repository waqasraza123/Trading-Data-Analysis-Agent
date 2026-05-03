from collections.abc import Iterable
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.candles.repository import CandleRepository
from app.modules.candles.schemas import CandleUpsertStatus
from app.modules.candles.validator import validate_candle
from app.modules.data_sources.models import DataSource, DataSourceStatus, DataSourceType
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.provider_polling.adapters.base import (
    ProviderPollingAdapterException,
    ProviderPollingFetchRequest,
    ProviderPollingResult,
)
from app.modules.provider_polling.adapters.registry import get_provider_polling_adapter
from app.modules.provider_polling.models import (
    ProviderPollingError,
    ProviderPollingRequest,
    ProviderPollingRequestStatus,
)
from app.modules.provider_polling.normalizer import normalize_provider_candle
from app.modules.provider_polling.repository import ProviderPollingRepository
from app.modules.provider_polling.schemas import (
    ProviderCandle,
    ProviderPollingErrorItem,
    ProviderPollingRequestCreate,
)
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository

SENSITIVE_METADATA_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "bearer",
        "password",
        "secret",
        "token",
    }
)


class ProviderPollingService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repository = ProviderPollingRepository(session)
        self.candle_repository = CandleRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def create_request(
        self,
        payload: ProviderPollingRequestCreate,
    ) -> ProviderPollingRequest:
        adapter = get_provider_polling_adapter(payload.provider.value)
        self.validate_request_metadata(payload.request_metadata_json)
        symbol, data_source = await self.load_symbol_and_source(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
        )
        effective_limit = self.effective_limit(payload.limit)
        polling_request = await self.repository.create_request(
            ProviderPollingRequest(
                workspace_id=payload.workspace_id,
                source_id=payload.source_id,
                symbol_id=payload.symbol_id,
                provider=payload.provider.value,
                provider_symbol=payload.provider_symbol,
                timeframe=payload.timeframe.value,
                start_time=payload.start_time,
                end_time=payload.end_time,
                limit=payload.limit,
                status=ProviderPollingRequestStatus.PENDING,
                request_metadata_json={
                    **payload.request_metadata_json,
                    "effectiveLimit": effective_limit,
                },
                response_metadata_json={},
                received_candle_count=0,
                stored_candle_count=0,
                skipped_candle_count=0,
            )
        )
        await self.session.flush()
        try:
            polling_request.status = ProviderPollingRequestStatus.RUNNING
            polling_request.started_at = utc_now()
            self.validate_polling_boundary(symbol=symbol, data_source=data_source)
            result = await adapter.fetch_candles(
                ProviderPollingFetchRequest(
                    provider=payload.provider.value,
                    provider_symbol=payload.provider_symbol,
                    timeframe=payload.timeframe,
                    start_time=payload.start_time,
                    end_time=payload.end_time,
                    limit=effective_limit,
                    timeout_seconds=self.settings.provider_polling_timeout_seconds,
                    user_agent=self.settings.provider_polling_user_agent,
                    binance_public_rest_base_url=self.settings.binance_public_rest_base_url,
                    request_metadata_json=payload.request_metadata_json,
                )
            )
            await self.process_provider_result(
                polling_request=polling_request,
                result=result,
                symbol=symbol,
                data_source=data_source,
            )
            await self.session.commit()
            await self.session.refresh(polling_request)
            return polling_request
        except ProviderPollingAdapterException as error:
            await self.mark_request_failed(
                polling_request=polling_request,
                error_code=error.code,
                error_message=error.message,
                raw_item_json=None,
            )
            await self.session.commit()
            await self.session.refresh(polling_request)
            return polling_request
        except (AppError, ValidationError) as error:
            await self.mark_request_failed(
                polling_request=polling_request,
                error_code=self.error_code(error),
                error_message=self.error_message(error),
                raw_item_json=None,
            )
            await self.session.commit()
            await self.session.refresh(polling_request)
            return polling_request

    async def get_request(self, request_id: UUID) -> ProviderPollingRequest:
        polling_request = await self.repository.get_request(request_id)
        if polling_request is None:
            raise AppError(404, "provider_polling_request_not_found", "Polling request not found")
        return polling_request

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
        return await self.repository.list_requests(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            status=status,
            provider=provider,
            symbol_id=symbol_id,
            source_id=source_id,
        )

    async def list_errors(
        self,
        request_id: UUID,
        limit: int,
        offset: int,
    ) -> list[ProviderPollingError]:
        await self.get_request(request_id)
        return await self.repository.list_errors(
            polling_request_id=request_id,
            limit=limit,
            offset=offset,
        )

    async def process_provider_result(
        self,
        polling_request: ProviderPollingRequest,
        result: ProviderPollingResult,
        symbol: Symbol,
        data_source: DataSource,
    ) -> None:
        stored_count = 0
        skipped_count = 0
        error_count = 0
        polling_request.requested_url = string_or_none(
            result.provider_metadata.get("requested_url")
        )
        polling_request.received_candle_count = len(result.candles)
        for warning in result.warnings:
            await self.repository.add_error(
                ProviderPollingError(
                    workspace_id=polling_request.workspace_id,
                    polling_request_id=polling_request.id,
                    error_code=warning.code,
                    error_message=warning.message,
                    raw_item_json=None,
                )
            )
            error_count += 1
        for provider_error in result.errors:
            await self.add_error_item(polling_request, provider_error)
            error_count += 1
        if not result.candles and not result.errors and not result.warnings:
            await self.repository.add_error(
                ProviderPollingError(
                    workspace_id=polling_request.workspace_id,
                    polling_request_id=polling_request.id,
                    error_code="provider_returned_no_candles",
                    error_message="Provider returned no candles",
                    raw_item_json=None,
                )
            )
            error_count += 1
        for provider_candle in result.candles:
            outcome = await self.store_provider_candle(
                polling_request=polling_request,
                provider_candle=provider_candle,
                symbol=symbol,
                data_source=data_source,
            )
            if outcome == "stored":
                stored_count += 1
            elif outcome == "error":
                skipped_count += 1
                error_count += 1
            else:
                skipped_count += 1
        polling_request.stored_candle_count = stored_count
        polling_request.skipped_candle_count = skipped_count
        polling_request.response_metadata_json = {
            **self.safe_metadata(result.provider_metadata),
            "warningCount": len(result.warnings),
            "providerErrorCount": len(result.errors),
            "recordedErrorCount": error_count,
        }
        polling_request.status = self.final_status(
            stored_count=stored_count,
            skipped_count=skipped_count,
            error_count=error_count,
            warning_count=len(result.warnings),
        )
        if polling_request.status == ProviderPollingRequestStatus.FAILED:
            polling_request.error_message = self.failed_request_message(result)
        polling_request.completed_at = utc_now()

    async def store_provider_candle(
        self,
        polling_request: ProviderPollingRequest,
        provider_candle: ProviderCandle,
        symbol: Symbol,
        data_source: DataSource,
    ) -> str:
        try:
            candle = normalize_provider_candle(
                provider_candle=provider_candle,
                workspace_id=polling_request.workspace_id,
                symbol_id=polling_request.symbol_id,
                source_id=polling_request.source_id,
                polling_request_id=polling_request.id,
            )
            validation_result = validate_candle(
                candle=candle,
                symbol=symbol,
                data_source=data_source,
            )
            if not validation_result.is_valid:
                for issue in validation_result.issues:
                    await self.repository.add_error(
                        ProviderPollingError(
                            workspace_id=polling_request.workspace_id,
                            polling_request_id=polling_request.id,
                            error_code=issue.code.value,
                            error_message=issue.message,
                            raw_item_json=provider_candle.raw_item_json,
                        )
                    )
                return "error"
            upsert_result = await self.candle_repository.upsert_normalized_candle(candle)
        except (AppError, ValidationError, ValueError) as error:
            await self.repository.add_error(
                ProviderPollingError(
                    workspace_id=polling_request.workspace_id,
                    polling_request_id=polling_request.id,
                    error_code=self.error_code(error),
                    error_message=self.error_message(error),
                    raw_item_json=provider_candle.raw_item_json,
                )
            )
            return "error"
        if upsert_result.status == CandleUpsertStatus.CONFLICTING_FINAL:
            await self.repository.add_error(
                ProviderPollingError(
                    workspace_id=polling_request.workspace_id,
                    polling_request_id=polling_request.id,
                    error_code="conflicting_final_candle",
                    error_message=upsert_result.message,
                    raw_item_json=provider_candle.raw_item_json,
                )
            )
            return "error"
        if upsert_result.status in {
            CandleUpsertStatus.DUPLICATE_FINAL,
            CandleUpsertStatus.IGNORED_LATE_PARTIAL,
        }:
            return "skipped"
        return "stored"

    async def mark_request_failed(
        self,
        polling_request: ProviderPollingRequest,
        error_code: str,
        error_message: str,
        raw_item_json: dict[str, object] | None,
    ) -> None:
        polling_request.status = ProviderPollingRequestStatus.FAILED
        polling_request.error_message = truncate(error_message, 2000)
        polling_request.completed_at = utc_now()
        await self.repository.add_error(
            ProviderPollingError(
                workspace_id=polling_request.workspace_id,
                polling_request_id=polling_request.id,
                error_code=error_code,
                error_message=truncate(error_message, 2000),
                raw_item_json=raw_item_json,
            )
        )

    async def add_error_item(
        self,
        polling_request: ProviderPollingRequest,
        error_item: ProviderPollingErrorItem,
    ) -> None:
        await self.repository.add_error(
            ProviderPollingError(
                workspace_id=polling_request.workspace_id,
                polling_request_id=polling_request.id,
                error_code=error_item.code,
                error_message=error_item.message,
                raw_item_json=error_item.raw_item_json,
            )
        )

    async def load_symbol_and_source(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID,
    ) -> tuple[Symbol, DataSource]:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        data_source = await self.data_source_repository.get_by_id(source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if data_source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )
        return symbol, data_source

    def validate_polling_boundary(self, symbol: Symbol, data_source: DataSource) -> None:
        if data_source.source_type != DataSourceType.API_POLLING:
            raise AppError(
                422,
                "invalid_provider_polling_source_type",
                "Provider polling requires an api_polling data source",
            )
        if data_source.status != DataSourceStatus.ACTIVE:
            raise AppError(422, "inactive_source", "Inactive sources cannot be polled")
        if not symbol.is_active:
            raise AppError(422, "inactive_symbol", "Inactive symbols cannot be polled")

    def effective_limit(self, requested_limit: int | None) -> int:
        max_limit = self.settings.provider_polling_max_candles_per_request
        if requested_limit is None:
            return max_limit
        if requested_limit > max_limit:
            raise AppError(
                422,
                "provider_polling_limit_too_large",
                "Provider polling limit exceeds configured maximum",
            )
        return requested_limit

    def validate_request_metadata(self, metadata: dict[str, Any]) -> None:
        sensitive_path = find_sensitive_metadata_path(metadata)
        if sensitive_path is not None:
            raise AppError(
                422,
                "provider_polling_secret_metadata_rejected",
                f"Provider polling metadata must not include sensitive key '{sensitive_path}'",
            )

    def safe_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in metadata.items()
            if not key_contains_secret(key)
        }

    def final_status(
        self,
        stored_count: int,
        skipped_count: int,
        error_count: int,
        warning_count: int,
    ) -> ProviderPollingRequestStatus:
        if stored_count == 0:
            return ProviderPollingRequestStatus.FAILED
        if skipped_count > 0 or error_count > 0 or warning_count > 0:
            return ProviderPollingRequestStatus.COMPLETED_WITH_WARNINGS
        return ProviderPollingRequestStatus.COMPLETED

    def failed_request_message(self, result: ProviderPollingResult) -> str:
        first_error = next(iter(result.errors), None)
        if first_error is not None:
            return first_error.message
        if result.warnings:
            return result.warnings[0].message
        if not result.candles:
            return "Provider returned no candles"
        return "Provider polling request failed"

    def error_code(self, error: Exception) -> str:
        if isinstance(error, AppError):
            return error.code
        if isinstance(error, ValidationError):
            return "invalid_provider_candle"
        return "provider_polling_failed"

    def error_message(self, error: Exception) -> str:
        if isinstance(error, AppError):
            return error.message
        if isinstance(error, ValidationError):
            return str(error.errors()[0]["msg"])
        return "Provider polling failed"


def find_sensitive_metadata_path(value: object, path: tuple[str, ...] = ()) -> str | None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            key_text = str(key)
            next_path = (*path, key_text)
            if key_contains_secret(key_text):
                return ".".join(next_path)
            nested_match = find_sensitive_metadata_path(nested_value, next_path)
            if nested_match is not None:
                return nested_match
    if isinstance(value, list):
        return find_sensitive_list_path(value, path)
    return None


def find_sensitive_list_path(values: Iterable[object], path: tuple[str, ...]) -> str | None:
    for index, nested_value in enumerate(values):
        nested_match = find_sensitive_metadata_path(nested_value, (*path, str(index)))
        if nested_match is not None:
            return nested_match
    return None


def key_contains_secret(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(secret_key in normalized for secret_key in SENSITIVE_METADATA_KEYS)


def string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def truncate(value: str, max_length: int) -> str:
    return value if len(value) <= max_length else value[:max_length]
