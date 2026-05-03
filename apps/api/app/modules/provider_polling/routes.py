from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.provider_polling.models import ProviderPollingRequestStatus
from app.modules.provider_polling.schemas import (
    ProviderPollingErrorRead,
    ProviderPollingProvider,
    ProviderPollingRequestCreate,
    ProviderPollingRequestRead,
)
from app.modules.provider_polling.service import ProviderPollingService

router = APIRouter(prefix="/provider-polling", tags=["provider-polling"])


def get_provider_polling_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ProviderPollingService:
    return ProviderPollingService(session=session, settings=request.app.state.settings)


@router.post(
    "/requests",
    response_model=ProviderPollingRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_provider_polling_request(
    payload: ProviderPollingRequestCreate,
    service: Annotated[ProviderPollingService, Depends(get_provider_polling_service)],
) -> ProviderPollingRequestRead:
    polling_request = await service.create_request(payload)
    return ProviderPollingRequestRead.model_validate(polling_request)


@router.get("/requests", response_model=list[ProviderPollingRequestRead])
async def list_provider_polling_requests(
    service: Annotated[ProviderPollingService, Depends(get_provider_polling_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
    status_filter: Annotated[ProviderPollingRequestStatus | None, Query(alias="status")] = None,
    provider: ProviderPollingProvider | None = None,
    symbol_id: UUID | None = None,
    source_id: UUID | None = None,
) -> list[ProviderPollingRequestRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    polling_requests = await service.list_requests(
        limit=pagination.limit,
        offset=pagination.offset,
        workspace_id=workspace_id,
        status=status_filter.value if status_filter is not None else None,
        provider=provider.value if provider is not None else None,
        symbol_id=symbol_id,
        source_id=source_id,
    )
    return [
        ProviderPollingRequestRead.model_validate(polling_request)
        for polling_request in polling_requests
    ]


@router.get("/requests/{request_id}", response_model=ProviderPollingRequestRead)
async def get_provider_polling_request(
    request_id: UUID,
    service: Annotated[ProviderPollingService, Depends(get_provider_polling_service)],
) -> ProviderPollingRequestRead:
    polling_request = await service.get_request(request_id)
    return ProviderPollingRequestRead.model_validate(polling_request)


@router.get("/requests/{request_id}/errors", response_model=list[ProviderPollingErrorRead])
async def list_provider_polling_errors(
    request_id: UUID,
    service: Annotated[ProviderPollingService, Depends(get_provider_polling_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ProviderPollingErrorRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    errors = await service.list_errors(
        request_id=request_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [ProviderPollingErrorRead.model_validate(error) for error in errors]
