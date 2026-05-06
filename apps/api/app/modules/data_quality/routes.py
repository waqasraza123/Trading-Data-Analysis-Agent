from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.data_quality.schemas import (
    DataQualityCandleRangeRequest,
    DataQualityFindingRead,
    DataQualityRunRead,
    DataQualitySourceRunRequest,
)
from app.modules.data_quality.service import DataQualityService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


def get_data_quality_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> DataQualityService:
    return DataQualityService(session)


@router.post(
    "/candle-range/run",
    response_model=DataQualityRunRead,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def run_candle_range_quality(
    request: DataQualityCandleRangeRequest,
    service: Annotated[DataQualityService, Depends(get_data_quality_service)],
) -> DataQualityRunRead:
    return DataQualityRunRead.model_validate(await service.run_candle_range(request))


@router.post(
    "/data-sources/{source_id}/run",
    response_model=DataQualityRunRead,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def run_source_quality(
    source_id: UUID,
    request: DataQualitySourceRunRequest,
    service: Annotated[DataQualityService, Depends(get_data_quality_service)],
) -> DataQualityRunRead:
    run = await service.run_source(request.workspace_id, source_id)
    return DataQualityRunRead.model_validate(run)


@router.post(
    "/live-subscriptions/{subscription_id}/run",
    response_model=DataQualityRunRead,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def run_live_subscription_quality(
    subscription_id: UUID,
    request: DataQualitySourceRunRequest,
    service: Annotated[DataQualityService, Depends(get_data_quality_service)],
) -> DataQualityRunRead:
    return DataQualityRunRead.model_validate(
        await service.run_live_subscription(request.workspace_id, subscription_id)
    )


@router.get("/runs/{run_id}", response_model=DataQualityRunRead)
async def get_data_quality_run(
    run_id: UUID,
    service: Annotated[DataQualityService, Depends(get_data_quality_service)],
) -> DataQualityRunRead:
    return DataQualityRunRead.model_validate(await service.get_run(run_id))


@router.get("/runs/{run_id}/findings", response_model=list[DataQualityFindingRead])
async def list_data_quality_findings(
    run_id: UUID,
    service: Annotated[DataQualityService, Depends(get_data_quality_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DataQualityFindingRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    findings = await service.list_findings(run_id, pagination.limit, pagination.offset)
    return [DataQualityFindingRead.model_validate(finding) for finding in findings]
