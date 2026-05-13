from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.equity_data.credentials import EquityCredentialResolver
from app.modules.equity_data.csv_import import EquityCsvRowError
from app.modules.equity_data.models import (
    EquityDataImportError,
    EquityDataOperation,
    EquityDataOperationStatus,
    EquityDataOperationType,
    EquityDataProviderRequest,
)
from app.modules.equity_data.normalizer import normalize_provider, safe_reference
from app.modules.equity_data.repository import EquityDataRepository
from app.modules.equity_data.schemas import (
    EquityCatalystOperationRequest,
    EquityDataOperationRunMode,
    EquityDataOperationRetryRequest,
    EquityEnrichmentOperationRequest,
    EquityOperationUniverseImportRequest,
    EquityProviderUniverseImportRequest,
    EquitySymbolProviderRequest,
    EquityUniverseImportRowsRequest,
)
from app.modules.equity_data.service import EquityDataService, truncate
from app.modules.equity_research.repository import EquityResearchRepository
from app.modules.job_queue.models import JobQueueJobType, JobQueuePriority
from app.modules.job_queue.schemas import JobQueueJobCreate
from app.modules.job_queue.service import JobQueueService

COUNTER_KEYS = (
    "rows_received",
    "rows_processed",
    "symbols_created",
    "symbols_updated",
    "snapshots_written",
    "events_written",
    "catalysts_created",
    "warnings_count",
    "errors_count",
)


class EquityDataOperationCancelled(Exception):
    pass


class EquityDataOperationService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: EquityDataRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or EquityDataRepository(session)
        self.data_service = EquityDataService(session, self.settings, self.repository)
        self.job_service = JobQueueService(session, self.settings)
        self.credential_resolver = EquityCredentialResolver(session, self.settings)
        self.equity_repository = EquityResearchRepository(session)

    async def list_operations(
        self,
        workspace_id: UUID,
        status: str | None,
        operation_type: str | None,
        provider_name: str | None,
        limit: int,
        offset: int,
    ) -> list[EquityDataOperation]:
        await self.data_service.validate_workspace(workspace_id)
        return await self.repository.list_operations(
            workspace_id,
            status,
            operation_type,
            normalize_provider(provider_name) if provider_name else None,
            limit,
            offset,
        )

    async def get_operation_summary(
        self,
        workspace_id: UUID,
        problem_limit: int,
    ) -> dict[str, object]:
        await self.data_service.validate_workspace(workspace_id)
        status_counts = await self.repository.count_operations_by_status(workspace_id)
        operation_type_counts = await self.repository.count_operations_by_type(workspace_id)
        provider_counts = await self.repository.count_operations_by_provider(workspace_id)
        recent_problem_operations = await self.repository.list_recent_problem_operations(
            workspace_id,
            problem_limit,
        )
        return {
            "workspace_id": workspace_id,
            "total_count": sum(status_counts.values()),
            "active_count": sum(
                status_counts.get(status, 0)
                for status in active_operation_statuses()
            ),
            "terminal_count": sum(
                status_counts.get(status, 0)
                for status in terminal_operation_statuses()
            ),
            "warning_count": status_counts.get(
                EquityDataOperationStatus.COMPLETED_WITH_WARNINGS.value,
                0,
            ),
            "failed_count": status_counts.get(EquityDataOperationStatus.FAILED.value, 0),
            "cancelled_count": status_counts.get(
                EquityDataOperationStatus.CANCELLED.value,
                0,
            ),
            "latest_operation_at": await self.repository.get_latest_operation_timestamp(
                workspace_id
            ),
            "status_counts": status_counts,
            "operation_type_counts": operation_type_counts,
            "provider_counts": provider_counts,
            "recentProblemOperations": recent_problem_operations,
        }

    async def get_operation(self, operation_id: UUID) -> EquityDataOperation:
        operation = await self.repository.get_operation(operation_id)
        if operation is None:
            raise AppError(
                404,
                "equity_data_operation_not_found",
                "Equity data operation not found",
            )
        return operation

    async def list_operation_errors(
        self,
        operation: EquityDataOperation,
        limit: int = 25,
    ) -> list[EquityDataImportError]:
        if operation.linked_provider_request_id is None:
            return []
        return await self.repository.list_import_errors(
            operation.linked_provider_request_id,
            limit,
            0,
        )

    async def submit_universe_import(
        self,
        payload: EquityOperationUniverseImportRequest,
    ) -> EquityDataOperation:
        await self.data_service.validate_workspace(payload.workspace_id)
        operation_type = (
            EquityDataOperationType.PROVIDER_UNIVERSE_IMPORT
            if payload.provider != "csv_equity_import" or not payload.rows
            else EquityDataOperationType.UNIVERSE_IMPORT_ROWS
        )
        request_payload = payload.model_dump(mode="json", by_alias=True)
        existing = await self.get_existing_idempotent_operation(
            payload.workspace_id,
            payload.idempotency_key,
            operation_type,
            payload.provider,
            payload.dry_run,
        )
        if existing is not None:
            return existing
        operation = await self.create_operation(
            workspace_id=payload.workspace_id,
            operation_type=operation_type,
            provider_name=payload.provider,
            request_payload=request_payload,
            dry_run=payload.dry_run,
            idempotency_key=payload.idempotency_key,
        )
        if self.should_run_sync(payload.run_mode, len(payload.rows)):
            await self.execute_operation(operation.id, request_payload)
            return await self.get_operation(operation.id)
        return await self.enqueue_operation(operation, request_payload)

    async def submit_enrichment(
        self,
        operation_type: EquityDataOperationType,
        payload: EquityEnrichmentOperationRequest,
    ) -> EquityDataOperation:
        await self.data_service.validate_workspace(payload.workspace_id)
        existing = await self.get_existing_idempotent_operation(
            payload.workspace_id,
            payload.idempotency_key,
            operation_type,
            payload.provider,
            payload.dry_run,
        )
        if existing is not None:
            return existing
        await self.ensure_provider_ready(
            payload.workspace_id,
            payload.provider,
            payload.credential_ref_id,
        )
        request_payload = payload.model_dump(mode="json", by_alias=True) | {
            "operationType": operation_type.value
        }
        operation = await self.create_operation(
            workspace_id=payload.workspace_id,
            operation_type=operation_type,
            provider_name=payload.provider,
            request_payload=request_payload,
            dry_run=payload.dry_run,
            idempotency_key=payload.idempotency_key,
        )
        if payload.run_mode == EquityDataOperationRunMode.SYNC:
            await self.execute_operation(operation.id, request_payload)
            return await self.get_operation(operation.id)
        return await self.enqueue_operation(operation, request_payload)

    async def submit_catalyst_conversion(
        self,
        payload: EquityCatalystOperationRequest,
    ) -> EquityDataOperation:
        await self.data_service.validate_workspace(payload.workspace_id)
        request_payload = payload.model_dump(mode="json", by_alias=True) | {
            "operationType": EquityDataOperationType.EARNINGS_TO_CATALYSTS.value
        }
        existing = await self.get_existing_idempotent_operation(
            payload.workspace_id,
            payload.idempotency_key,
            EquityDataOperationType.EARNINGS_TO_CATALYSTS,
            None,
            payload.dry_run,
        )
        if existing is not None:
            return existing
        operation = await self.create_operation(
            workspace_id=payload.workspace_id,
            operation_type=EquityDataOperationType.EARNINGS_TO_CATALYSTS,
            provider_name=None,
            request_payload=request_payload,
            dry_run=payload.dry_run,
            idempotency_key=payload.idempotency_key,
        )
        if payload.run_mode == EquityDataOperationRunMode.SYNC:
            await self.execute_operation(operation.id, request_payload)
            return await self.get_operation(operation.id)
        return await self.enqueue_operation(operation, request_payload)

    async def create_file_import_operation(
        self,
        payload: EquityUniverseImportRowsRequest,
        run_mode: EquityDataOperationRunMode,
        dry_run: bool,
        validation_errors: list[EquityCsvRowError],
        received_count: int,
        idempotency_key: str | None = None,
    ) -> EquityDataOperation:
        request_payload = payload.model_dump(mode="json", by_alias=True) | {
            "runMode": run_mode.value,
            "dryRun": dry_run,
            "csvValidationErrors": [error.__dict__ for error in validation_errors],
            "rowsReceived": received_count,
        }
        operation = await self.create_operation(
            workspace_id=payload.workspace_id,
            operation_type=EquityDataOperationType.UNIVERSE_IMPORT_FILE,
            provider_name=payload.provider,
            request_payload=request_payload,
            dry_run=dry_run,
            idempotency_key=idempotency_key,
        )
        return await self.enqueue_operation(operation, request_payload)

    async def create_operation(
        self,
        workspace_id: UUID,
        operation_type: EquityDataOperationType,
        provider_name: str | None,
        request_payload: dict[str, Any],
        dry_run: bool,
        idempotency_key: str | None,
    ) -> EquityDataOperation:
        operation = EquityDataOperation(
            workspace_id=workspace_id,
            operation_type=operation_type.value,
            provider_name=provider_name,
            status=EquityDataOperationStatus.PENDING.value,
            idempotency_key=idempotency_key,
            progress_current=0,
            progress_total=None,
            progress_message="Operation queued",
            counters_json=empty_counters(),
            request_summary_json=operation_request_summary(request_payload),
            result_summary_json={},
            error_summary_json={},
            dry_run=dry_run,
        )
        return await self.repository.create_operation(operation)

    async def enqueue_operation(
        self,
        operation: EquityDataOperation,
        request_payload: dict[str, Any],
    ) -> EquityDataOperation:
        job = await self.job_service.enqueue_job(
            JobQueueJobCreate(
                workspace_id=operation.workspace_id,
                queue_name="equity_data",
                job_type=JobQueueJobType.EQUITY_DATA_OPERATION,
                priority=JobQueuePriority.NORMAL,
                idempotency_key=operation.idempotency_key,
                payload_json=safe_reference(
                    {
                        "operationId": str(operation.id),
                        "operationType": operation.operation_type,
                        "request": request_payload,
                    }
                ),
                max_attempts=1,
            ),
            commit=False,
        )
        operation.linked_job_id = job.id
        operation.progress_message = "Operation pending background execution"
        updated = await self.repository.update_operation(operation)
        await self.session.commit()
        return updated

    async def cancel_operation(
        self,
        operation_id: UUID,
        reason: str | None,
    ) -> EquityDataOperation:
        operation = await self.get_operation(operation_id)
        if operation.status in terminal_operation_statuses():
            return operation
        if operation.linked_job_id is not None:
            await self.job_service.cancel_job(operation.linked_job_id, reason=reason, commit=False)
        operation.status = EquityDataOperationStatus.CANCELLED.value
        operation.finished_at = datetime.now(UTC)
        operation.progress_message = "Operation cancelled"
        operation.error_summary_json = safe_reference({"reason": reason} if reason else {})
        updated = await self.repository.update_operation(operation)
        await self.session.commit()
        return updated

    async def retry_operation(
        self,
        operation_id: UUID,
        payload: EquityDataOperationRetryRequest,
    ) -> EquityDataOperation:
        original = await self.get_operation(operation_id)
        await self.data_service.validate_workspace(original.workspace_id)
        if original.status not in retryable_operation_statuses():
            raise AppError(
                422,
                "equity_data_operation_retry_not_allowed",
                "Only warning, failed, and cancelled equity data operations can be retried",
            )
        operation_type = coerce_operation_type(original.operation_type)
        request_payload = await self.get_replayable_operation_payload(original)
        request_payload = request_payload | {
            "runMode": payload.run_mode.value,
            "retryOfOperationId": str(original.id),
        }
        if payload.reason is not None:
            request_payload["retryReason"] = payload.reason
        existing = await self.get_existing_idempotent_operation(
            original.workspace_id,
            payload.idempotency_key,
            operation_type,
            original.provider_name,
            original.dry_run,
        )
        if existing is not None:
            return existing
        retry = await self.create_operation(
            workspace_id=original.workspace_id,
            operation_type=operation_type,
            provider_name=original.provider_name,
            request_payload=request_payload,
            dry_run=original.dry_run,
            idempotency_key=payload.idempotency_key,
        )
        if self.should_retry_sync(payload.run_mode, operation_type, request_payload):
            await self.execute_operation(retry.id, request_payload)
            return await self.get_operation(retry.id)
        return await self.enqueue_operation(retry, request_payload)

    async def get_replayable_operation_payload(
        self,
        operation: EquityDataOperation,
    ) -> dict[str, Any]:
        payload = await self.get_replayable_job_payload(operation)
        if payload is None:
            payload = dict(operation.request_summary_json or {})
        if not payload:
            raise AppError(
                422,
                "equity_data_operation_retry_payload_missing",
                "Operation does not have a retryable request payload",
            )
        if str(payload.get("workspaceId") or "") != str(operation.workspace_id):
            raise AppError(
                422,
                "equity_data_operation_retry_payload_invalid",
                "Operation request payload does not match its workspace",
            )
        if operation.operation_type in {
            EquityDataOperationType.UNIVERSE_IMPORT_ROWS.value,
            EquityDataOperationType.UNIVERSE_IMPORT_FILE.value,
        } and not isinstance(payload.get("rows"), list):
            raise AppError(
                422,
                "equity_data_operation_retry_rows_unavailable",
                "Operation row payload is not available for retry",
            )
        safe_payload = safe_reference(payload)
        if safe_payload.get("truncated") is True:
            raise AppError(
                422,
                "equity_data_operation_retry_payload_too_large",
                "Operation request payload is too large to retry safely",
            )
        return safe_payload

    async def get_replayable_job_payload(
        self,
        operation: EquityDataOperation,
    ) -> dict[str, Any] | None:
        if operation.linked_job_id is None:
            return None
        try:
            job = await self.job_service.get_job(operation.linked_job_id)
        except AppError as error:
            if error.code == "job_queue_job_not_found":
                return None
            raise
        request = job.payload_json.get("request")
        return dict(request) if isinstance(request, dict) else None

    def should_retry_sync(
        self,
        run_mode: EquityDataOperationRunMode,
        operation_type: EquityDataOperationType,
        payload: dict[str, Any],
    ) -> bool:
        if run_mode == EquityDataOperationRunMode.SYNC:
            return True
        if run_mode == EquityDataOperationRunMode.QUEUED:
            return False
        if operation_type in {
            EquityDataOperationType.UNIVERSE_IMPORT_ROWS,
            EquityDataOperationType.UNIVERSE_IMPORT_FILE,
        }:
            rows = payload.get("rows")
            row_count = len(rows) if isinstance(rows, list) else 0
            return self.should_run_sync(run_mode, row_count)
        return False

    async def execute_operation(
        self,
        operation_id: UUID,
        request_payload: dict[str, Any] | None = None,
    ) -> EquityDataOperation:
        operation = await self.get_operation(operation_id)
        if operation.status == EquityDataOperationStatus.CANCELLED.value:
            return operation
        payload = request_payload or operation.request_summary_json
        try:
            await self.start_operation(operation, payload)
            await self.ensure_operation_not_cancelled(operation)
            if operation.operation_type in {
                EquityDataOperationType.UNIVERSE_IMPORT_ROWS.value,
                EquityDataOperationType.UNIVERSE_IMPORT_FILE.value,
            }:
                result = await self.execute_rows_import(operation, payload)
            elif operation.operation_type == EquityDataOperationType.PROVIDER_UNIVERSE_IMPORT.value:
                result = await self.execute_provider_universe_import(operation, payload)
            elif operation.operation_type in {
                EquityDataOperationType.METADATA_ENRICHMENT.value,
                EquityDataOperationType.FUNDAMENTALS_ENRICHMENT.value,
                EquityDataOperationType.EARNINGS_ENRICHMENT.value,
            }:
                result = await self.execute_symbol_enrichment(operation, payload)
            elif operation.operation_type == EquityDataOperationType.EARNINGS_TO_CATALYSTS.value:
                result = await self.execute_earnings_to_catalysts(operation, payload)
            else:
                raise AppError(
                    422,
                    "equity_data_operation_type_unsupported",
                    "Equity data operation type is not supported",
                )
        except EquityDataOperationCancelled:
            return await self.get_operation(operation.id)
        except Exception as error:
            return await self.fail_operation(operation, error)
        return await self.complete_operation(operation, result)

    async def execute_rows_import(
        self,
        operation: EquityDataOperation,
        payload: dict[str, Any],
    ) -> EquityDataProviderRequest | dict[str, Any]:
        rows = payload.get("rows")
        if not isinstance(rows, list) or not rows:
            raise AppError(422, "equity_data_rows_required", "Rows are required")
        await self.update_progress(operation, 0, len(rows), "Importing research universe rows")
        if operation.dry_run:
            return {"rowsReceived": len(rows), "dryRun": True}
        request = await self.data_service.import_universe_from_rows(
            EquityUniverseImportRowsRequest.model_validate(payload)
        )
        operation.linked_provider_request_id = request.id
        await self.record_payload_validation_errors(
            request,
            payload.get("csvValidationErrors"),
        )
        await self.update_operation_counters_from_request(operation, request)
        await self.update_progress(operation, len(rows), len(rows), "Universe import completed")
        return request

    async def execute_provider_universe_import(
        self,
        operation: EquityDataOperation,
        payload: dict[str, Any],
    ) -> EquityDataProviderRequest | dict[str, Any]:
        await self.ensure_provider_ready(
            operation.workspace_id,
            str(payload.get("provider") or operation.provider_name or ""),
            coerce_uuid(payload.get("credentialRefId")),
        )
        await self.update_progress(operation, 0, 1, "Importing provider research universe")
        if operation.dry_run:
            return {"provider": payload.get("provider"), "dryRun": True}
        request = await self.data_service.import_universe_from_provider(
            EquityProviderUniverseImportRequest.model_validate(payload)
        )
        operation.linked_provider_request_id = request.id
        await self.update_operation_counters_from_request(operation, request)
        await self.update_progress(operation, 1, 1, "Provider universe import completed")
        return request

    async def execute_symbol_enrichment(
        self,
        operation: EquityDataOperation,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        provider = str(payload.get("provider") or operation.provider_name or "")
        credential_ref_id = coerce_uuid(payload.get("credentialRefId"))
        await self.ensure_provider_ready(operation.workspace_id, provider, credential_ref_id)
        symbol_ids = await self.resolve_symbol_ids(
            operation.workspace_id,
            [coerce_uuid(value) for value in payload.get("symbolIds", []) if coerce_uuid(value)],
            coerce_uuid(payload.get("universeId")),
            int(payload.get("limit") or 100),
        )
        await self.update_progress(operation, 0, len(symbol_ids), "Running symbol enrichment")
        if operation.dry_run:
            return {"symbolCount": len(symbol_ids), "dryRun": True}
        stored = 0
        errors = 0
        linked_request_id: UUID | None = None
        for index, symbol_id in enumerate(symbol_ids, start=1):
            await self.ensure_operation_not_cancelled(operation)
            try:
                request_payload = EquitySymbolProviderRequest(
                    workspaceId=operation.workspace_id,
                    provider=provider,
                    credentialRefId=credential_ref_id,
                    filters=payload.get("filters")
                    if isinstance(payload.get("filters"), dict)
                    else {},
                )
                if operation.operation_type == EquityDataOperationType.METADATA_ENRICHMENT.value:
                    request = await self.data_service.lookup_and_store_metadata(
                        symbol_id,
                        request_payload,
                    )
                elif (
                    operation.operation_type
                    == EquityDataOperationType.FUNDAMENTALS_ENRICHMENT.value
                ):
                    request = await self.data_service.fetch_and_store_fundamentals(
                        symbol_id,
                        request_payload,
                    )
                else:
                    request = await self.data_service.fetch_and_store_earnings(
                        symbol_id,
                        request_payload,
                    )
                linked_request_id = linked_request_id or request.id
                stored += request.stored_count
            except Exception:
                errors += 1
            await self.update_progress(
                operation,
                index,
                len(symbol_ids),
                "Running symbol enrichment",
            )
        operation.linked_provider_request_id = linked_request_id
        counters = empty_counters()
        counters["rows_processed"] = len(symbol_ids)
        if operation.operation_type == EquityDataOperationType.EARNINGS_ENRICHMENT.value:
            counters["events_written"] = stored
        else:
            counters["snapshots_written"] = stored
        counters["errors_count"] = errors
        operation.counters_json = counters
        return {"symbolCount": len(symbol_ids), "storedCount": stored, "errors": errors}

    async def execute_earnings_to_catalysts(
        self,
        operation: EquityDataOperation,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        symbol_ids = await self.resolve_symbol_ids(
            operation.workspace_id,
            [coerce_uuid(value) for value in payload.get("symbolIds", []) if coerce_uuid(value)],
            coerce_uuid(payload.get("universeId")),
            int(payload.get("limit") or 100),
        )
        events = await self.repository.list_earnings_events_for_symbols(
            operation.workspace_id,
            symbol_ids,
            int(payload.get("limit") or 100),
        )
        await self.update_progress(operation, 0, len(events), "Converting earnings context")
        created = 0
        skipped = 0
        if not operation.dry_run:
            for index, event in enumerate(events, start=1):
                await self.ensure_operation_not_cancelled(operation)
                existing = await self.repository.get_catalyst_for_earnings_event(
                    operation.workspace_id,
                    event.id,
                )
                if existing is None:
                    await self.data_service.convert_earnings_to_catalyst_context(event.id)
                    created += 1
                else:
                    skipped += 1
                await self.update_progress(
                    operation,
                    index,
                    len(events),
                    "Converting earnings context",
                )
        counters = empty_counters()
        counters["rows_processed"] = len(events)
        counters["catalysts_created"] = created
        counters["warnings_count"] = skipped
        operation.counters_json = counters
        return {"eventsReviewed": len(events), "catalystsCreated": created, "skipped": skipped}

    async def resolve_symbol_ids(
        self,
        workspace_id: UUID,
        symbol_ids: list[UUID],
        universe_id: UUID | None,
        limit: int,
    ) -> list[UUID]:
        if symbol_ids:
            return symbol_ids[:limit]
        if universe_id is None:
            raise AppError(
                422,
                "equity_data_scope_required",
                "Universe or symbol scope is required",
            )
        return await self.repository.list_universe_symbol_ids(workspace_id, universe_id, limit)

    async def ensure_provider_ready(
        self,
        workspace_id: UUID,
        provider_name: str,
        credential_ref_id: UUID | None,
    ) -> None:
        resolution = await self.credential_resolver.resolve_credential_ref(
            provider_name,
            credential_ref_id,
            workspace_id,
        )
        if not resolution.ready:
            raise AppError(422, resolution.status, resolution.message)

    async def start_operation(
        self,
        operation: EquityDataOperation,
        payload: dict[str, Any],
    ) -> None:
        await self.ensure_operation_not_cancelled(operation)
        operation.status = EquityDataOperationStatus.RUNNING.value
        operation.started_at = operation.started_at or datetime.now(UTC)
        operation.progress_message = "Operation running"
        operation.request_summary_json = operation_request_summary(payload)
        await self.repository.update_operation(operation)
        await self.session.commit()

    async def update_progress(
        self,
        operation: EquityDataOperation,
        current: int,
        total: int | None,
        message: str,
    ) -> None:
        operation.progress_current = current
        operation.progress_total = total
        operation.progress_message = message
        await self.repository.update_operation(operation)
        await self.session.commit()

    async def ensure_operation_not_cancelled(self, operation: EquityDataOperation) -> None:
        await self.session.refresh(operation)
        if operation.status == EquityDataOperationStatus.CANCELLED.value:
            raise EquityDataOperationCancelled

    async def complete_operation(
        self,
        operation: EquityDataOperation,
        result: EquityDataProviderRequest | dict[str, Any],
    ) -> EquityDataOperation:
        if operation.status == EquityDataOperationStatus.CANCELLED.value:
            return operation
        if isinstance(result, EquityDataProviderRequest):
            completed_with_warnings = result.failed_count > 0
            operation.result_summary_json = safe_reference(result.response_summary_json)
        else:
            completed_with_warnings = int(operation.counters_json.get("errors_count") or 0) > 0
            operation.result_summary_json = safe_reference(result)
        operation.status = (
            EquityDataOperationStatus.COMPLETED_WITH_WARNINGS.value
            if completed_with_warnings
            else EquityDataOperationStatus.COMPLETED.value
        )
        operation.finished_at = datetime.now(UTC)
        operation.progress_message = "Operation completed"
        updated = await self.repository.update_operation(operation)
        await self.session.commit()
        return updated

    async def fail_operation(
        self,
        operation: EquityDataOperation,
        error: Exception,
    ) -> EquityDataOperation:
        operation.status = EquityDataOperationStatus.FAILED.value
        operation.finished_at = datetime.now(UTC)
        operation.error_summary_json = safe_reference(
            {
                "errorCode": error.code if isinstance(error, AppError) else type(error).__name__,
                "message": error.message if isinstance(error, AppError) else str(error),
            }
        )
        operation.progress_message = "Operation failed"
        counters = empty_counters() | dict(operation.counters_json or {})
        counters["errors_count"] = int(counters.get("errors_count") or 0) + 1
        operation.counters_json = counters
        updated = await self.repository.update_operation(operation)
        await self.session.commit()
        return updated

    async def update_operation_counters_from_request(
        self,
        operation: EquityDataOperation,
        request: EquityDataProviderRequest,
    ) -> None:
        counters = empty_counters()
        counters["rows_received"] = request.received_count
        counters["rows_processed"] = request.stored_count + request.skipped_count
        counters["symbols_updated"] = request.stored_count
        counters["snapshots_written"] = request.stored_count
        counters["warnings_count"] = request.skipped_count
        counters["errors_count"] = request.failed_count
        operation.counters_json = counters
        await self.repository.update_operation(operation)
        await self.session.commit()

    async def record_payload_validation_errors(
        self,
        request: EquityDataProviderRequest,
        raw_errors: object,
    ) -> None:
        if not isinstance(raw_errors, list):
            return
        for raw_error in raw_errors:
            if not isinstance(raw_error, dict):
                continue
            await self.repository.add_import_error(
                EquityDataImportError(
                    workspace_id=request.workspace_id,
                    provider_request_id=request.id,
                    row_number=raw_error.get("row_number"),
                    error_code=truncate(str(raw_error.get("error_code") or "csv_row_invalid"), 80)
                    or "csv_row_invalid",
                    error_message=truncate(
                        str(raw_error.get("error_message") or "CSV row failed validation"),
                        1000,
                    )
                    or "CSV row failed validation",
                    raw_item_json=safe_reference(raw_error.get("raw_item_json") or {}),
                )
            )
        await self.session.commit()

    async def get_existing_idempotent_operation(
        self,
        workspace_id: UUID,
        idempotency_key: str | None,
        operation_type: EquityDataOperationType,
        provider_name: str | None,
        dry_run: bool,
    ) -> EquityDataOperation | None:
        if idempotency_key is None:
            return None
        existing = await self.repository.get_operation_by_idempotency_key(
            workspace_id,
            idempotency_key,
        )
        if existing is None:
            return None
        if (
            existing.operation_type != operation_type.value
            or existing.provider_name != provider_name
            or existing.dry_run != dry_run
        ):
            raise AppError(
                409,
                "equity_data_operation_idempotency_conflict",
                "Idempotency key is already used by a different equity data operation",
            )
        return existing

    def should_run_sync(self, run_mode: EquityDataOperationRunMode, row_count: int) -> bool:
        if run_mode == EquityDataOperationRunMode.SYNC:
            return True
        if run_mode == EquityDataOperationRunMode.QUEUED:
            return False
        return row_count > 0 and row_count <= self.settings.equity_data_sync_import_row_threshold


def empty_counters() -> dict[str, int]:
    return {key: 0 for key in COUNTER_KEYS}


def operation_request_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = safe_reference(payload)
    if "rows" in summary and isinstance(summary["rows"], list):
        summary["rows"] = {
            "count": len(summary["rows"]),
            "preview": summary["rows"][:5],
        }
    if "csvValidationErrors" in summary and isinstance(summary["csvValidationErrors"], list):
        summary["csvValidationErrors"] = {"count": len(summary["csvValidationErrors"])}
    return summary


def coerce_uuid(value: object) -> UUID | None:
    if value in {None, ""}:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        return None


def coerce_operation_type(value: str) -> EquityDataOperationType:
    try:
        return EquityDataOperationType(value)
    except ValueError as error:
        raise AppError(
            422,
            "equity_data_operation_type_unsupported",
            "Equity data operation type is not supported",
        ) from error


def terminal_operation_statuses() -> set[str]:
    return {
        EquityDataOperationStatus.COMPLETED.value,
        EquityDataOperationStatus.COMPLETED_WITH_WARNINGS.value,
        EquityDataOperationStatus.FAILED.value,
        EquityDataOperationStatus.CANCELLED.value,
    }


def active_operation_statuses() -> set[str]:
    return {
        EquityDataOperationStatus.PENDING.value,
        EquityDataOperationStatus.RUNNING.value,
    }


def retryable_operation_statuses() -> set[str]:
    return {
        EquityDataOperationStatus.COMPLETED_WITH_WARNINGS.value,
        EquityDataOperationStatus.FAILED.value,
        EquityDataOperationStatus.CANCELLED.value,
    }
