from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.data_sources.models import DataSourceStatus, DataSourceType
from app.modules.data_sources.schemas import DataSourceCreate, DataSourceRead, DataSourceUpdate
from app.modules.data_sources.service import DataSourceService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


def get_data_source_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> DataSourceService:
    return DataSourceService(session)


@router.post(
    "",
    response_model=DataSourceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def create_data_source(
    payload: DataSourceCreate,
    service: Annotated[DataSourceService, Depends(get_data_source_service)],
) -> DataSourceRead:
    data_source = await service.create_data_source(payload)
    return DataSourceRead.model_validate(data_source)


@router.get("", response_model=list[DataSourceRead])
async def list_data_sources(
    service: Annotated[DataSourceService, Depends(get_data_source_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
    source_type: DataSourceType | None = None,
    status_filter: Annotated[DataSourceStatus | None, Query(alias="status")] = None,
) -> list[DataSourceRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    data_sources = await service.list_data_sources(
        limit=pagination.limit,
        offset=pagination.offset,
        workspace_id=workspace_id,
        source_type=source_type.value if source_type else None,
        status=status_filter.value if status_filter else None,
    )
    return [DataSourceRead.model_validate(data_source) for data_source in data_sources]


@router.get("/{data_source_id}", response_model=DataSourceRead)
async def get_data_source(
    data_source_id: UUID,
    service: Annotated[DataSourceService, Depends(get_data_source_service)],
) -> DataSourceRead:
    data_source = await service.get_data_source(data_source_id)
    return DataSourceRead.model_validate(data_source)


@router.patch(
    "/{data_source_id}",
    response_model=DataSourceRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def update_data_source(
    data_source_id: UUID,
    payload: DataSourceUpdate,
    service: Annotated[DataSourceService, Depends(get_data_source_service)],
) -> DataSourceRead:
    data_source = await service.update_data_source(data_source_id, payload)
    return DataSourceRead.model_validate(data_source)
