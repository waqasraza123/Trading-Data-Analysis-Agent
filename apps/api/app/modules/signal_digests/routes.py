from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.signal_digests.models import (
    SignalDigestItemType,
    SignalDigestStatus,
    SignalDigestType,
)
from app.modules.signal_digests.schemas import (
    DailySignalDigestRequest,
    SessionSignalDigestRequest,
    SignalDigestCreate,
    SignalDigestItemRead,
    SignalDigestRunListFilters,
    SignalDigestRunRead,
)
from app.modules.signal_digests.service import SignalDigestService

router = APIRouter(prefix="/signal-digests", tags=["signal-digests"])


def get_signal_digest_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> SignalDigestService:
    return SignalDigestService(session)


@router.post("", response_model=SignalDigestRunRead, status_code=status.HTTP_201_CREATED)
async def create_signal_digest(
    payload: SignalDigestCreate,
    service: Annotated[SignalDigestService, Depends(get_signal_digest_service)],
) -> SignalDigestRunRead:
    run = await service.create_digest(payload)
    return SignalDigestRunRead.model_validate(run)


@router.get("", response_model=list[SignalDigestRunRead])
async def list_signal_digests(
    service: Annotated[SignalDigestService, Depends(get_signal_digest_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    digest_type: Annotated[SignalDigestType | None, Query(alias="digestType")] = None,
    status_filter: Annotated[SignalDigestStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SignalDigestRunRead]:
    runs = await service.list_digests(
        SignalDigestRunListFilters(
            workspace_id=workspace_id,
            digest_type=digest_type,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    )
    return [SignalDigestRunRead.model_validate(run) for run in runs]


@router.get("/{digest_id}", response_model=SignalDigestRunRead)
async def get_signal_digest(
    digest_id: UUID,
    service: Annotated[SignalDigestService, Depends(get_signal_digest_service)],
) -> SignalDigestRunRead:
    run = await service.get_digest(digest_id)
    return SignalDigestRunRead.model_validate(run)


@router.get("/{digest_id}/items", response_model=list[SignalDigestItemRead])
async def list_signal_digest_items(
    digest_id: UUID,
    service: Annotated[SignalDigestService, Depends(get_signal_digest_service)],
    item_type: Annotated[SignalDigestItemType | None, Query(alias="itemType")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SignalDigestItemRead]:
    items = await service.list_digest_items(
        digest_id=digest_id,
        item_type=item_type.value if item_type is not None else None,
        limit=limit,
        offset=offset,
    )
    return [SignalDigestItemRead.model_validate(item) for item in items]


@router.post("/daily", response_model=SignalDigestRunRead, status_code=status.HTTP_201_CREATED)
async def create_daily_signal_digest(
    payload: DailySignalDigestRequest,
    service: Annotated[SignalDigestService, Depends(get_signal_digest_service)],
) -> SignalDigestRunRead:
    run = await service.build_daily_digest(
        workspace_id=payload.workspace_id,
        digest_date=payload.date,
        timezone=payload.timezone,
        filters=payload.filters,
        max_items=payload.max_items,
    )
    return SignalDigestRunRead.model_validate(run)


@router.post("/session", response_model=SignalDigestRunRead, status_code=status.HTTP_201_CREATED)
async def create_session_signal_digest(
    payload: SessionSignalDigestRequest,
    service: Annotated[SignalDigestService, Depends(get_signal_digest_service)],
) -> SignalDigestRunRead:
    run = await service.build_session_digest(
        workspace_id=payload.workspace_id,
        session_label=payload.session_label.value,
        digest_date=payload.date,
        timezone=payload.timezone,
        filters=payload.filters,
        max_items=payload.max_items,
    )
    return SignalDigestRunRead.model_validate(run)
