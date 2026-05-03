from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.engine_executions.models import EngineExecutionStatus
from app.modules.engine_executions.schemas import (
    EngineExecutionCreate,
    EngineExecutionEventRead,
    EngineExecutionRead,
)
from app.modules.engine_executions.service import EngineExecutionService

router = APIRouter(prefix="/engine-executions", tags=["engine-executions"])


def get_engine_execution_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> EngineExecutionService:
    return EngineExecutionService(session)


@router.post("", response_model=EngineExecutionRead, status_code=status.HTTP_201_CREATED)
async def create_engine_execution(
    payload: EngineExecutionCreate,
    service: Annotated[EngineExecutionService, Depends(get_engine_execution_service)],
) -> EngineExecutionRead:
    record = await service.create_record(payload)
    return EngineExecutionRead.model_validate(record)


@router.get("", response_model=list[EngineExecutionRead])
async def list_engine_executions(
    service: Annotated[EngineExecutionService, Depends(get_engine_execution_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
    status_filter: Annotated[EngineExecutionStatus | None, Query(alias="status")] = None,
    engine_name: str | None = None,
    operation_type: str | None = None,
    source_type: str | None = None,
    source_id: UUID | None = None,
) -> list[EngineExecutionRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    records = await service.list_records(
        limit=pagination.limit,
        offset=pagination.offset,
        workspace_id=workspace_id,
        status=status_filter,
        engine_name=engine_name,
        operation_type=operation_type,
        source_type=source_type,
        source_id=source_id,
    )
    return [EngineExecutionRead.model_validate(record) for record in records]


@router.get("/{record_id}", response_model=EngineExecutionRead)
async def get_engine_execution(
    record_id: UUID,
    service: Annotated[EngineExecutionService, Depends(get_engine_execution_service)],
) -> EngineExecutionRead:
    record = await service.get_record(record_id)
    return EngineExecutionRead.model_validate(record)


@router.get("/{record_id}/events", response_model=list[EngineExecutionEventRead])
async def list_engine_execution_events(
    record_id: UUID,
    service: Annotated[EngineExecutionService, Depends(get_engine_execution_service)],
) -> list[EngineExecutionEventRead]:
    events = await service.list_events(record_id)
    return [EngineExecutionEventRead.model_validate(event) for event in events]


@router.post("/{record_id}/cancel", response_model=EngineExecutionRead)
async def cancel_engine_execution(
    record_id: UUID,
    service: Annotated[EngineExecutionService, Depends(get_engine_execution_service)],
) -> EngineExecutionRead:
    record = await service.cancel_record(record_id)
    return EngineExecutionRead.model_validate(record)
