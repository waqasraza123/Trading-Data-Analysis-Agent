from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.symbols.schemas import SymbolCreate, SymbolRead, SymbolUpdate
from app.modules.symbols.service import SymbolService

router = APIRouter(prefix="/symbols", tags=["symbols"])


def get_symbol_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> SymbolService:
    return SymbolService(session)


@router.post(
    "",
    response_model=SymbolRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def create_symbol(
    payload: SymbolCreate,
    service: Annotated[SymbolService, Depends(get_symbol_service)],
) -> SymbolRead:
    symbol = await service.create_symbol(payload)
    return SymbolRead.model_validate(symbol)


@router.get("", response_model=list[SymbolRead])
async def list_symbols(
    service: Annotated[SymbolService, Depends(get_symbol_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    is_active: bool | None = None,
) -> list[SymbolRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    symbols = await service.list_symbols(
        limit=pagination.limit,
        offset=pagination.offset,
        is_active=is_active,
    )
    return [SymbolRead.model_validate(symbol) for symbol in symbols]


@router.get("/{symbol_id}", response_model=SymbolRead)
async def get_symbol(
    symbol_id: UUID,
    service: Annotated[SymbolService, Depends(get_symbol_service)],
) -> SymbolRead:
    symbol = await service.get_symbol(symbol_id)
    return SymbolRead.model_validate(symbol)


@router.patch(
    "/{symbol_id}",
    response_model=SymbolRead,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def update_symbol(
    symbol_id: UUID,
    payload: SymbolUpdate,
    service: Annotated[SymbolService, Depends(get_symbol_service)],
) -> SymbolRead:
    symbol = await service.update_symbol(symbol_id, payload)
    return SymbolRead.model_validate(symbol)
