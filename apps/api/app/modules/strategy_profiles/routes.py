from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.strategy_profiles.schemas import StrategyProfileRead
from app.modules.strategy_profiles.service import StrategyProfileService

router = APIRouter(prefix="/strategy-profiles", tags=["strategy-profiles"])


def get_strategy_profile_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> StrategyProfileService:
    return StrategyProfileService(session)


@router.get("", response_model=list[StrategyProfileRead])
async def list_strategy_profiles(
    service: Annotated[StrategyProfileService, Depends(get_strategy_profile_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    is_active: bool | None = None,
) -> list[StrategyProfileRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    profiles = await service.list_profiles(
        limit=pagination.limit,
        offset=pagination.offset,
        is_active=is_active,
    )
    return [StrategyProfileRead.model_validate(profile) for profile in profiles]


@router.get("/{key}", response_model=StrategyProfileRead)
async def get_strategy_profile(
    key: str,
    service: Annotated[StrategyProfileService, Depends(get_strategy_profile_service)],
) -> StrategyProfileRead:
    profile = await service.get_by_key(key)
    return StrategyProfileRead.model_validate(profile)
