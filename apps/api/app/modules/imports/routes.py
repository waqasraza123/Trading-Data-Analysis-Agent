from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.candles.timeframes import Timeframe
from app.modules.imports.schemas import (
    CsvCandleImportRequest,
    ImportBatchRead,
    ImportErrorRead,
    JsonCandleImportRequest,
)
from app.modules.imports.service import ImportService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/imports", tags=["imports"])


def get_import_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ImportService:
    return ImportService(session)


@router.post(
    "/candles/json",
    response_model=ImportBatchRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.IMPORTS_WRITE))],
)
async def import_json_candles(
    payload: JsonCandleImportRequest,
    service: Annotated[ImportService, Depends(get_import_service)],
) -> ImportBatchRead:
    batch = await service.process_json_import(payload)
    return ImportBatchRead.model_validate(batch)


@router.post(
    "/candles/csv",
    response_model=ImportBatchRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.IMPORTS_WRITE))],
)
async def import_csv_candles(
    request: Request,
    service: Annotated[ImportService, Depends(get_import_service)],
    workspace_id: Annotated[UUID, Form()],
    source_id: Annotated[UUID, Form()],
    symbol_id: Annotated[UUID, Form()],
    timeframe: Annotated[Timeframe, Form()],
    file: Annotated[UploadFile, File()],
    user_id: Annotated[UUID | None, Form()] = None,
) -> ImportBatchRead:
    file_bytes = await file.read()
    settings = request.app.state.settings
    if len(file_bytes) > settings.max_upload_file_bytes:
        raise AppError(413, "upload_file_too_large", "Upload file is too large")
    try:
        csv_text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AppError(422, "invalid_csv_encoding", "CSV file must be UTF-8 encoded") from error
    payload = CsvCandleImportRequest(
        workspace_id=workspace_id,
        user_id=user_id,
        source_id=source_id,
        symbol_id=symbol_id,
        timeframe=timeframe,
        file_name=file.filename,
    )
    batch = await service.process_csv_import(payload=payload, csv_text=csv_text)
    return ImportBatchRead.model_validate(batch)


@router.get("/{import_batch_id}", response_model=ImportBatchRead)
async def get_import_batch(
    import_batch_id: UUID,
    service: Annotated[ImportService, Depends(get_import_service)],
) -> ImportBatchRead:
    batch = await service.get_import_batch(import_batch_id)
    return ImportBatchRead.model_validate(batch)


@router.get("/{import_batch_id}/errors", response_model=list[ImportErrorRead])
async def list_import_errors(
    import_batch_id: UUID,
    service: Annotated[ImportService, Depends(get_import_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ImportErrorRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    import_errors = await service.list_import_errors(
        import_batch_id=import_batch_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [ImportErrorRead.model_validate(import_error) for import_error in import_errors]
