from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.trading_journal.models import JournalDecisionType, JournalEntryStatus
from app.modules.trading_journal.schemas import (
    JournalEntryAttachmentCreateRequest,
    JournalEntryAttachmentRead,
    JournalEntryCreateRequest,
    JournalEntryRead,
    JournalEntryReviewCreateRequest,
    JournalEntryReviewRead,
    JournalEntryUpdateRequest,
)
from app.modules.trading_journal.service import TradingJournalService

router = APIRouter(prefix="/journal-entries", tags=["journal-entries"])


def get_trading_journal_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> TradingJournalService:
    return TradingJournalService(session)


@router.post("", response_model=JournalEntryRead, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    payload: JournalEntryCreateRequest,
    service: Annotated[TradingJournalService, Depends(get_trading_journal_service)],
) -> JournalEntryRead:
    return await service.create_journal_entry(payload)


@router.get("", response_model=list[JournalEntryRead])
async def list_journal_entries(
    service: Annotated[TradingJournalService, Depends(get_trading_journal_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    user_id: Annotated[UUID | None, Query(alias="userId")] = None,
    signal_id: Annotated[UUID | None, Query(alias="signalId")] = None,
    analysis_run_id: Annotated[UUID | None, Query(alias="analysisRunId")] = None,
    decision_type: Annotated[
        JournalDecisionType | None,
        Query(alias="decisionType"),
    ] = None,
    entry_status: Annotated[JournalEntryStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[JournalEntryRead]:
    return await service.list_journal_entries(
        workspace_id=workspace_id,
        user_id=user_id,
        signal_id=signal_id,
        analysis_run_id=analysis_run_id,
        decision_type=decision_type.value if decision_type is not None else None,
        status=entry_status.value if entry_status is not None else None,
        limit=limit,
        offset=offset,
    )


@router.get("/{entry_id}", response_model=JournalEntryRead)
async def get_journal_entry(
    entry_id: UUID,
    service: Annotated[TradingJournalService, Depends(get_trading_journal_service)],
) -> JournalEntryRead:
    return await service.get_journal_entry(entry_id)


@router.patch("/{entry_id}", response_model=JournalEntryRead)
async def update_journal_entry(
    entry_id: UUID,
    payload: JournalEntryUpdateRequest,
    service: Annotated[TradingJournalService, Depends(get_trading_journal_service)],
) -> JournalEntryRead:
    return await service.update_journal_entry(entry_id, payload)


@router.post("/{entry_id}/archive", response_model=JournalEntryRead)
async def archive_journal_entry(
    entry_id: UUID,
    service: Annotated[TradingJournalService, Depends(get_trading_journal_service)],
) -> JournalEntryRead:
    return await service.archive_journal_entry(entry_id)


@router.post(
    "/{entry_id}/attachments",
    response_model=JournalEntryAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def attach_journal_reference(
    entry_id: UUID,
    payload: JournalEntryAttachmentCreateRequest,
    service: Annotated[TradingJournalService, Depends(get_trading_journal_service)],
) -> JournalEntryAttachmentRead:
    return await service.attach_reference(entry_id, payload)


@router.post(
    "/{entry_id}/review",
    response_model=JournalEntryReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def review_journal_entry(
    entry_id: UUID,
    payload: JournalEntryReviewCreateRequest,
    service: Annotated[TradingJournalService, Depends(get_trading_journal_service)],
) -> JournalEntryReviewRead:
    return await service.review_journal_entry_against_outcome(
        entry_id=entry_id,
        outcome_id=payload.outcome_id,
        metadata=payload.metadata,
    )


@router.get("/{entry_id}/reviews", response_model=list[JournalEntryReviewRead])
async def list_journal_reviews(
    entry_id: UUID,
    service: Annotated[TradingJournalService, Depends(get_trading_journal_service)],
) -> list[JournalEntryReviewRead]:
    return await service.list_journal_reviews(entry_id)
