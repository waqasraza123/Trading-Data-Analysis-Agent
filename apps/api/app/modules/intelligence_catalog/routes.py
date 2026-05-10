from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.intelligence_catalog.models import IntelligenceCatalogArtifactType
from app.modules.intelligence_catalog.schemas import (
    IntelligenceCatalogIndexRequest,
    IntelligenceCatalogItemRead,
    IntelligenceCatalogReindexRead,
    IntelligenceCatalogReindexRequest,
    IntelligenceCatalogRemoveRequest,
    IntelligenceCatalogSearchQuery,
    IntelligenceCatalogSearchRead,
    IntelligenceCatalogUpsert,
)
from app.modules.intelligence_catalog.service import IntelligenceCatalogService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/intelligence-catalog", tags=["intelligence-catalog"])


def get_intelligence_catalog_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> IntelligenceCatalogService:
    return IntelligenceCatalogService(session)


@router.post(
    "/index",
    response_model=IntelligenceCatalogItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def index_intelligence_artifact(
    payload: IntelligenceCatalogIndexRequest,
    service: Annotated[IntelligenceCatalogService, Depends(get_intelligence_catalog_service)],
) -> IntelligenceCatalogItemRead:
    item = await service.index_artifact(payload.artifact_type, payload.artifact_id)
    return IntelligenceCatalogItemRead.model_validate(item)


@router.post(
    "/items",
    response_model=IntelligenceCatalogItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def upsert_intelligence_catalog_item(
    payload: IntelligenceCatalogUpsert,
    service: Annotated[IntelligenceCatalogService, Depends(get_intelligence_catalog_service)],
) -> IntelligenceCatalogItemRead:
    item = await service.upsert_catalog_item(payload)
    return IntelligenceCatalogItemRead.model_validate(item)


@router.delete(
    "/items",
    response_model=dict[str, bool],
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def remove_intelligence_catalog_item(
    payload: IntelligenceCatalogRemoveRequest,
    service: Annotated[IntelligenceCatalogService, Depends(get_intelligence_catalog_service)],
) -> dict[str, bool]:
    return {"removed": await service.remove_catalog_item(payload)}


@router.post(
    "/reindex",
    response_model=IntelligenceCatalogReindexRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def reindex_intelligence_catalog(
    payload: IntelligenceCatalogReindexRequest,
    service: Annotated[IntelligenceCatalogService, Depends(get_intelligence_catalog_service)],
) -> IntelligenceCatalogReindexRead:
    return await service.reindex_workspace(payload)


@router.get("/search", response_model=IntelligenceCatalogSearchRead)
async def search_intelligence_catalog(
    service: Annotated[IntelligenceCatalogService, Depends(get_intelligence_catalog_service)],
    workspace_id: UUID,
    query: str | None = None,
    artifact_types: Annotated[list[IntelligenceCatalogArtifactType] | None, Query()] = None,
    status: str | None = None,
    symbol_id: UUID | None = None,
    timeframe: str | None = None,
    strategy_profile_key: str | None = None,
    pattern_type: str | None = None,
    bias: str | None = None,
    outcome_label: str | None = None,
    source_type: str | None = None,
    tags: Annotated[list[str] | None, Query()] = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IntelligenceCatalogSearchRead:
    search_query = IntelligenceCatalogSearchQuery(
        workspace_id=workspace_id,
        query=query,
        artifact_types=artifact_types,
        status=status,
        symbol_id=symbol_id,
        timeframe=timeframe,
        strategy_profile_key=strategy_profile_key,
        pattern_type=pattern_type,
        bias=bias,
        outcome_label=outcome_label,
        source_type=source_type,
        tags=tags,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    items = await service.search_catalog(search_query)
    return IntelligenceCatalogSearchRead(
        items=[IntelligenceCatalogItemRead.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
    )


@router.get("/items/{item_id}", response_model=IntelligenceCatalogItemRead)
async def get_intelligence_catalog_item(
    item_id: UUID,
    service: Annotated[IntelligenceCatalogService, Depends(get_intelligence_catalog_service)],
) -> IntelligenceCatalogItemRead:
    item = await service.get_catalog_item(item_id)
    return IntelligenceCatalogItemRead.model_validate(item)


@router.get("/by-artifact", response_model=IntelligenceCatalogItemRead)
async def get_intelligence_catalog_item_by_artifact(
    service: Annotated[IntelligenceCatalogService, Depends(get_intelligence_catalog_service)],
    workspace_id: UUID,
    artifact_type: IntelligenceCatalogArtifactType,
    artifact_id: UUID,
) -> IntelligenceCatalogItemRead:
    item = await service.get_by_artifact(
        workspace_id=workspace_id,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
    )
    return IntelligenceCatalogItemRead.model_validate(item)
