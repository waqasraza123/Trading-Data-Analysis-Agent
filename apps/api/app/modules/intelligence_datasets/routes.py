from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.intelligence_datasets.schemas import (
    IntelligenceDatasetExportCreate,
    IntelligenceDatasetExportItemRead,
    IntelligenceDatasetExportRead,
)
from app.modules.intelligence_datasets.service import IntelligenceDatasetService

router = APIRouter(prefix="/intelligence-datasets", tags=["intelligence-datasets"])


def get_intelligence_dataset_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> IntelligenceDatasetService:
    return IntelligenceDatasetService(session)


@router.post("/exports", response_model=IntelligenceDatasetExportRead)
async def create_intelligence_dataset_export(
    request: IntelligenceDatasetExportCreate,
    service: Annotated[IntelligenceDatasetService, Depends(get_intelligence_dataset_service)],
) -> IntelligenceDatasetExportRead:
    return IntelligenceDatasetExportRead.model_validate(await service.create_export(request))


@router.get("/exports", response_model=list[IntelligenceDatasetExportRead])
async def list_intelligence_dataset_exports(
    workspace_id: UUID,
    service: Annotated[IntelligenceDatasetService, Depends(get_intelligence_dataset_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IntelligenceDatasetExportRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    exports = await service.list_exports(workspace_id, pagination.limit, pagination.offset)
    return [IntelligenceDatasetExportRead.model_validate(export) for export in exports]


@router.get("/exports/{export_id}", response_model=IntelligenceDatasetExportRead)
async def get_intelligence_dataset_export(
    export_id: UUID,
    service: Annotated[IntelligenceDatasetService, Depends(get_intelligence_dataset_service)],
) -> IntelligenceDatasetExportRead:
    return IntelligenceDatasetExportRead.model_validate(await service.get_export(export_id))


@router.get("/exports/{export_id}/items", response_model=list[IntelligenceDatasetExportItemRead])
async def list_intelligence_dataset_export_items(
    export_id: UUID,
    service: Annotated[IntelligenceDatasetService, Depends(get_intelligence_dataset_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IntelligenceDatasetExportItemRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    items = await service.list_items(export_id, pagination.limit, pagination.offset)
    return [IntelligenceDatasetExportItemRead.model_validate(item) for item in items]


@router.get("/exports/{export_id}/jsonl")
async def get_intelligence_dataset_export_jsonl(
    export_id: UUID,
    service: Annotated[IntelligenceDatasetService, Depends(get_intelligence_dataset_service)],
) -> Response:
    return Response(
        content=await service.export_jsonl(export_id),
        media_type="application/x-ndjson",
    )
