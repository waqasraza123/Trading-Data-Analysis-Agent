from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.equity_data.models import EquityDataRequestStatus, EquityDataRequestType
from app.modules.equity_data.schemas import (
    EquityDataImportErrorRead,
    EquityDataProviderCapability,
    EquityDataProviderRequestRead,
    EquityDataProviderTestRead,
    EquityDataProviderTestRequest,
    EquityEarningsEventRead,
    EquityEarningsImportRowsRequest,
    EquityFundamentalSnapshotRead,
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


@router.get("/providers", response_model=list[EquityDataProviderCapability])
async def list_providers(
    service: Annotated[EquityDataService, Depends(get_equity_data_service)],
) -> list[EquityDataProviderCapability]:
    return await service.list_providers()


@router.post("/providers/{provider}/test", response_model=EquityDataProviderTestRead)
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
