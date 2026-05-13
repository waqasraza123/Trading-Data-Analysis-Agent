from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.equity_data.csv_import import parse_equity_universe_csv
from app.modules.equity_data.models import (
    EquityDataOperationType,
    EquityDataRequestStatus,
    EquityDataRequestType,
)
from app.modules.equity_data.operations import EquityDataOperationService
from app.modules.equity_data.schemas import (
    EquityCatalystOperationRequest,
    EquityDataOperationCancelRequest,
    EquityDataOperationAuditBundleRead,
    EquityDataImportErrorRead,
    EquityDataOperationDetailRead,
    EquityDataOperationDiagnosticsRead,
    EquityDataOperationLineageRead,
    EquityDataOperationListRead,
    EquityDataOperationRead,
    EquityDataOperationRecoveryPlanRead,
    EquityDataOperationRetryReadinessRead,
    EquityDataOperationReviewQueueRead,
    EquityDataOperationRetryRequest,
    EquityDataOperationRunMode,
    EquityDataOperationSummaryRead,
    EquityDataProviderCapability,
    EquityDataProviderRequestRead,
    EquityDataProviderTestRead,
    EquityDataProviderTestRequest,
    EquityEarningsEventRead,
    EquityEarningsImportRowsRequest,
    EquityEnrichmentOperationRequest,
    EquityFileImportRead,
    EquityFundamentalSnapshotRead,
    EquityOperationUniverseImportRequest,
    EquityProviderUniverseImportRequest,
    EquitySymbolMetadataSnapshotRead,
    EquitySymbolProviderRequest,
    EquityUniverseImportRowsRequest,
)
from app.modules.equity_data.service import EquityDataService
from app.modules.equity_research.schemas import EquityCatalystContextRead
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/equity-data", tags=["equity-data"])


def get_equity_data_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> EquityDataService:
    return EquityDataService(session)


def get_equity_data_operation_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> EquityDataOperationService:
    return EquityDataOperationService(session)


@router.get("/providers", response_model=list[EquityDataProviderCapability])
async def list_providers(
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> list[EquityDataProviderCapability]:
    return await service.list_providers()


@router.post(
    "/providers/{provider}/test",
    response_model=EquityDataProviderTestRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def test_provider(
    provider: str,
    payload: EquityDataProviderTestRequest,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> EquityDataProviderTestRead:
    status_value, message, configured = await service.test_provider(
        payload.workspace_id,
        provider,
        payload.credential_ref_id,
    )
    return EquityDataProviderTestRead(
        provider=provider,
        status=status_value,
        message=message,
        configured=configured,
    )


@router.post(
    "/universe-import/rows",
    response_model=EquityDataProviderRequestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def import_universe_rows(
    payload: EquityUniverseImportRowsRequest,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> EquityDataProviderRequestRead:
    request = await service.import_universe_from_rows(payload)
    return EquityDataProviderRequestRead.model_validate(request)


@router.post(
    "/universe-import/provider",
    response_model=EquityDataProviderRequestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def import_universe_provider(
    payload: EquityProviderUniverseImportRequest,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> EquityDataProviderRequestRead:
    request = await service.import_universe_from_provider(payload)
    return EquityDataProviderRequestRead.model_validate(request)


@router.get("/provider-requests", response_model=list[EquityDataProviderRequestRead])
async def list_provider_requests(
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
    workspace_id: UUID,
    provider: str | None = None,
    request_type: EquityDataRequestType | None = None,
    status_filter: Annotated[EquityDataRequestStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquityDataProviderRequestRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    requests = await service.list_provider_requests(
        workspace_id=workspace_id,
        provider=provider,
        request_type=request_type.value if request_type is not None else None,
        status=status_filter.value if status_filter is not None else None,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [EquityDataProviderRequestRead.model_validate(request) for request in requests]


@router.get("/provider-requests/{request_id}", response_model=EquityDataProviderRequestRead)
async def get_provider_request(
    request_id: UUID,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> EquityDataProviderRequestRead:
    request = await service.get_provider_request(request_id)
    return EquityDataProviderRequestRead.model_validate(request)


@router.get(
    "/provider-requests/{request_id}/errors",
    response_model=list[EquityDataImportErrorRead],
)
async def list_provider_request_errors(
    request_id: UUID,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquityDataImportErrorRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    errors = await service.list_request_errors(request_id, pagination.limit, pagination.offset)
    return [EquityDataImportErrorRead.model_validate(error) for error in errors]


@router.get("/operations", response_model=EquityDataOperationListRead)
async def list_operations(
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
    workspace_id: UUID,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    operation_type: str | None = None,
    provider_name: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EquityDataOperationListRead:
    pagination = PaginationParams(limit=limit, offset=offset)
    operations = await service.list_operations(
        workspace_id=workspace_id,
        status=status_filter,
        operation_type=operation_type,
        provider_name=provider_name,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return EquityDataOperationListRead(
        operations=[EquityDataOperationRead.model_validate(operation) for operation in operations]
    )


@router.get("/operations/summary", response_model=EquityDataOperationSummaryRead)
async def get_operation_summary(
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
    workspace_id: UUID,
    problem_limit: Annotated[int, Query(ge=0, le=25)] = 5,
) -> EquityDataOperationSummaryRead:
    summary = await service.get_operation_summary(
        workspace_id=workspace_id,
        problem_limit=problem_limit,
    )
    recent_problem_operations = summary.get("recentProblemOperations")
    if isinstance(recent_problem_operations, list):
        summary["recentProblemOperations"] = [
            EquityDataOperationRead.model_validate(operation)
            for operation in recent_problem_operations
        ]
    return EquityDataOperationSummaryRead.model_validate(summary)


@router.get("/operations/review-queue", response_model=EquityDataOperationReviewQueueRead)
async def get_operation_review_queue(
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
    workspace_id: UUID,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    stale_after_minutes: Annotated[int, Query(ge=5, le=1440)] = 30,
) -> EquityDataOperationReviewQueueRead:
    return await service.get_operation_review_queue(
        workspace_id=workspace_id,
        limit=limit,
        stale_after_minutes=stale_after_minutes,
    )


@router.get("/operations/{operation_id}/lineage", response_model=EquityDataOperationLineageRead)
async def get_operation_lineage(
    operation_id: UUID,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
    scan_limit: Annotated[int, Query(ge=25, le=500)] = 250,
) -> EquityDataOperationLineageRead:
    return await service.get_operation_lineage(operation_id, scan_limit)


@router.get(
    "/operations/{operation_id}/audit-bundle",
    response_model=EquityDataOperationAuditBundleRead,
)
async def get_operation_audit_bundle(
    operation_id: UUID,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
    error_limit: Annotated[int, Query(ge=0, le=100)] = 25,
    scan_limit: Annotated[int, Query(ge=25, le=500)] = 250,
    stale_after_minutes: Annotated[int, Query(ge=5, le=1440)] = 30,
) -> EquityDataOperationAuditBundleRead:
    return await service.get_operation_audit_bundle(
        operation_id=operation_id,
        error_limit=error_limit,
        scan_limit=scan_limit,
        stale_after_minutes=stale_after_minutes,
    )


@router.get(
    "/operations/{operation_id}/retry-readiness",
    response_model=EquityDataOperationRetryReadinessRead,
)
async def get_operation_retry_readiness(
    operation_id: UUID,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
    run_mode: EquityDataOperationRunMode = EquityDataOperationRunMode.QUEUED,
) -> EquityDataOperationRetryReadinessRead:
    return await service.get_operation_retry_readiness(operation_id, run_mode)


@router.get(
    "/operations/{operation_id}/recovery-plan",
    response_model=EquityDataOperationRecoveryPlanRead,
)
async def get_operation_recovery_plan(
    operation_id: UUID,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
    stale_after_minutes: Annotated[int, Query(ge=5, le=1440)] = 30,
) -> EquityDataOperationRecoveryPlanRead:
    return await service.get_operation_recovery_plan(operation_id, stale_after_minutes)


@router.get("/operations/{operation_id}", response_model=EquityDataOperationDetailRead)
async def get_operation(
    operation_id: UUID,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
) -> EquityDataOperationDetailRead:
    return await service.get_operation_detail(operation_id)


@router.get(
    "/operations/{operation_id}/diagnostics",
    response_model=EquityDataOperationDiagnosticsRead,
)
async def get_operation_diagnostics(
    operation_id: UUID,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
    error_limit: Annotated[int, Query(ge=0, le=100)] = 25,
) -> EquityDataOperationDiagnosticsRead:
    return await service.get_operation_diagnostics(operation_id, error_limit)


@router.post(
    "/operations/{operation_id}/cancel",
    response_model=EquityDataOperationRead,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def cancel_operation(
    operation_id: UUID,
    payload: EquityDataOperationCancelRequest,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
) -> EquityDataOperationRead:
    operation = await service.cancel_operation(operation_id, payload.reason)
    return EquityDataOperationRead.model_validate(operation)


@router.post(
    "/operations/{operation_id}/retry",
    response_model=EquityDataOperationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def retry_operation(
    operation_id: UUID,
    payload: EquityDataOperationRetryRequest,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
) -> EquityDataOperationRead:
    operation = await service.retry_operation(operation_id, payload)
    return EquityDataOperationRead.model_validate(operation)


@router.post(
    "/operations/universe-import",
    response_model=EquityDataOperationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def submit_universe_import_operation(
    payload: EquityOperationUniverseImportRequest,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
) -> EquityDataOperationRead:
    operation = await service.submit_universe_import(payload)
    return EquityDataOperationRead.model_validate(operation)


@router.post(
    "/operations/metadata-enrichment",
    response_model=EquityDataOperationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def submit_metadata_enrichment_operation(
    payload: EquityEnrichmentOperationRequest,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
) -> EquityDataOperationRead:
    operation = await service.submit_enrichment(
        EquityDataOperationType.METADATA_ENRICHMENT,
        payload,
    )
    return EquityDataOperationRead.model_validate(operation)


@router.post(
    "/operations/fundamentals-enrichment",
    response_model=EquityDataOperationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def submit_fundamentals_enrichment_operation(
    payload: EquityEnrichmentOperationRequest,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
) -> EquityDataOperationRead:
    operation = await service.submit_enrichment(
        EquityDataOperationType.FUNDAMENTALS_ENRICHMENT,
        payload,
    )
    return EquityDataOperationRead.model_validate(operation)


@router.post(
    "/operations/earnings-enrichment",
    response_model=EquityDataOperationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def submit_earnings_enrichment_operation(
    payload: EquityEnrichmentOperationRequest,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
) -> EquityDataOperationRead:
    operation = await service.submit_enrichment(
        EquityDataOperationType.EARNINGS_ENRICHMENT,
        payload,
    )
    return EquityDataOperationRead.model_validate(operation)


@router.post(
    "/operations/earnings-to-catalysts",
    response_model=EquityDataOperationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def submit_earnings_to_catalysts_operation(
    payload: EquityCatalystOperationRequest,
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
) -> EquityDataOperationRead:
    operation = await service.submit_catalyst_conversion(payload)
    return EquityDataOperationRead.model_validate(operation)


@router.post(
    "/operations/universe-import-file",
    response_model=EquityFileImportRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def import_universe_file(
    service: Annotated[EquityDataOperationService, Depends(get_equity_data_operation_service)],
    workspace_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    universe_id: Annotated[UUID | None, Form()] = None,
    create_universe_name: Annotated[str | None, Form()] = None,
    provider_name: Annotated[str, Form()] = "csv_equity_import",
    run_mode: Annotated[EquityDataOperationRunMode, Form()] = EquityDataOperationRunMode.AUTO,
    dry_run: Annotated[bool, Form()] = False,
) -> EquityFileImportRead:
    content = await file.read()
    parse_result = parse_equity_universe_csv(
        content,
        max_bytes=service.settings.max_upload_file_bytes,
        max_rows=service.settings.equity_data_max_queued_import_rows,
    )
    import_payload = EquityUniverseImportRowsRequest(
        workspaceId=workspace_id,
        universeId=universe_id,
        createUniverseName=create_universe_name,
        provider=provider_name,
        rows=parse_result.rows,
    )
    resolved_run_mode = (
        EquityDataOperationRunMode.SYNC
        if run_mode == EquityDataOperationRunMode.AUTO
        and len(parse_result.rows) <= service.settings.equity_data_sync_import_row_threshold
        else EquityDataOperationRunMode.QUEUED
        if run_mode == EquityDataOperationRunMode.AUTO
        else run_mode
    )
    if resolved_run_mode == EquityDataOperationRunMode.SYNC:
        operation = await service.submit_universe_import(
            EquityOperationUniverseImportRequest(
                workspaceId=workspace_id,
                universeId=universe_id,
                createUniverseName=create_universe_name,
                provider=provider_name,
                rows=parse_result.rows,
                runMode=EquityDataOperationRunMode.SYNC,
                dryRun=dry_run,
            )
        )
        if operation.linked_provider_request_id is not None:
            request = await service.data_service.get_provider_request(
                operation.linked_provider_request_id
            )
            await service.record_payload_validation_errors(
                request,
                [error.__dict__ for error in parse_result.errors],
            )
        else:
            request = None
        return EquityFileImportRead(
            runMode=resolved_run_mode,
            operation=EquityDataOperationRead.model_validate(operation),
            providerRequest=EquityDataProviderRequestRead.model_validate(request)
            if request
            else None,
            validationErrors=[],
            rowsReceived=parse_result.received_count,
            rowsValid=len(parse_result.rows),
        )
    operation = await service.create_file_import_operation(
        import_payload,
        run_mode=resolved_run_mode,
        dry_run=dry_run,
        validation_errors=parse_result.errors,
        received_count=parse_result.received_count,
    )
    return EquityFileImportRead(
        runMode=resolved_run_mode,
        operation=EquityDataOperationRead.model_validate(operation),
        providerRequest=None,
        validationErrors=[],
        rowsReceived=parse_result.received_count,
        rowsValid=len(parse_result.rows),
    )


@router.post(
    "/symbols/{symbol_id}/metadata/lookup",
    response_model=EquityDataProviderRequestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def lookup_symbol_metadata(
    symbol_id: UUID,
    payload: EquitySymbolProviderRequest,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> EquityDataProviderRequestRead:
    request = await service.lookup_and_store_metadata(symbol_id, payload)
    return EquityDataProviderRequestRead.model_validate(request)


@router.get(
    "/symbols/{symbol_id}/metadata/latest",
    response_model=EquitySymbolMetadataSnapshotRead | None,
)
async def get_latest_symbol_metadata(
    symbol_id: UUID,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
    workspace_id: UUID,
) -> EquitySymbolMetadataSnapshotRead | None:
    snapshot = await service.get_symbol_latest_metadata(workspace_id, symbol_id)
    return EquitySymbolMetadataSnapshotRead.model_validate(snapshot) if snapshot else None


@router.post(
    "/symbols/{symbol_id}/fundamentals/fetch",
    response_model=EquityDataProviderRequestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def fetch_symbol_fundamentals(
    symbol_id: UUID,
    payload: EquitySymbolProviderRequest,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> EquityDataProviderRequestRead:
    request = await service.fetch_and_store_fundamentals(symbol_id, payload)
    return EquityDataProviderRequestRead.model_validate(request)


@router.get(
    "/symbols/{symbol_id}/fundamentals/latest",
    response_model=EquityFundamentalSnapshotRead | None,
)
async def get_latest_symbol_fundamentals(
    symbol_id: UUID,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
    workspace_id: UUID,
) -> EquityFundamentalSnapshotRead | None:
    snapshot = await service.get_symbol_latest_fundamentals(workspace_id, symbol_id)
    return EquityFundamentalSnapshotRead.model_validate(snapshot) if snapshot else None


@router.post(
    "/symbols/{symbol_id}/earnings/fetch",
    response_model=EquityDataProviderRequestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def fetch_symbol_earnings(
    symbol_id: UUID,
    payload: EquitySymbolProviderRequest,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> EquityDataProviderRequestRead:
    request = await service.fetch_and_store_earnings(symbol_id, payload)
    return EquityDataProviderRequestRead.model_validate(request)


@router.get("/symbols/{symbol_id}/earnings", response_model=list[EquityEarningsEventRead])
async def list_symbol_earnings(
    symbol_id: UUID,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
    workspace_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquityEarningsEventRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    events = await service.list_symbol_earnings(
        workspace_id,
        symbol_id,
        pagination.limit,
        pagination.offset,
    )
    return [EquityEarningsEventRead.model_validate(event) for event in events]


@router.post(
    "/earnings/import-rows",
    response_model=EquityDataProviderRequestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def import_earnings_rows(
    payload: EquityEarningsImportRowsRequest,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> EquityDataProviderRequestRead:
    request = await service.import_earnings_rows(payload)
    return EquityDataProviderRequestRead.model_validate(request)


@router.post(
    "/earnings/{event_id}/create-catalyst-context",
    response_model=EquityCatalystContextRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def create_catalyst_from_earnings(
    event_id: UUID,
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> EquityCatalystContextRead:
    catalyst = await service.convert_earnings_to_catalyst_context(event_id)
    return EquityCatalystContextRead.model_validate(catalyst)
