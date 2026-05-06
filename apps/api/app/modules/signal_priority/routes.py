from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.signal_priority.models import SignalPriorityLabel, SignalReviewBucket
from app.modules.signal_priority.schemas import (
    SignalPriorityListFilters,
    SignalPriorityScoreRead,
    SignalPriorityWorkspaceScoreResponse,
)
from app.modules.signal_priority.service import SignalPriorityService

router = APIRouter(tags=["signal-priority"])


def get_signal_priority_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> SignalPriorityService:
    return SignalPriorityService(session)


@router.post(
    "/signals/{signal_id}/priority-score",
    response_model=SignalPriorityScoreRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def score_signal_priority(
    signal_id: UUID,
    service: Annotated[SignalPriorityService, Depends(get_signal_priority_service)],
    force_recompute: Annotated[bool, Query(alias="forceRecompute")] = False,
) -> SignalPriorityScoreRead:
    score = await service.score_signal(
        signal_id=signal_id,
        force_recompute=force_recompute,
    )
    return SignalPriorityScoreRead.model_validate(score)


@router.get("/signals/{signal_id}/priority-score", response_model=SignalPriorityScoreRead)
async def get_signal_priority_score(
    signal_id: UUID,
    service: Annotated[SignalPriorityService, Depends(get_signal_priority_service)],
) -> SignalPriorityScoreRead:
    score = await service.get_signal_priority(signal_id)
    return SignalPriorityScoreRead.model_validate(score)


@router.get("/signal-priorities", response_model=list[SignalPriorityScoreRead])
async def list_signal_priorities(
    service: Annotated[SignalPriorityService, Depends(get_signal_priority_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    priority_label: Annotated[
        SignalPriorityLabel | None,
        Query(alias="priorityLabel"),
    ] = None,
    review_bucket: Annotated[SignalReviewBucket | None, Query(alias="reviewBucket")] = None,
    symbol_id: Annotated[UUID | None, Query(alias="symbolId")] = None,
    timeframe: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SignalPriorityScoreRead]:
    scores = await service.list_prioritized_signals(
        SignalPriorityListFilters(
            workspace_id=workspace_id,
            priority_label=priority_label,
            review_bucket=review_bucket,
            symbol_id=symbol_id,
            timeframe=timeframe,
            limit=limit,
            offset=offset,
        )
    )
    return [SignalPriorityScoreRead.model_validate(score) for score in scores]


@router.post(
    "/signal-priorities/workspaces/{workspace_id}/score-recent",
    response_model=SignalPriorityWorkspaceScoreResponse,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def score_workspace_recent_signal_priorities(
    workspace_id: UUID,
    service: Annotated[SignalPriorityService, Depends(get_signal_priority_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 500,
    force_recompute: Annotated[bool, Query(alias="forceRecompute")] = False,
) -> SignalPriorityWorkspaceScoreResponse:
    scores, skipped_count = await service.score_workspace_recent_signals(
        workspace_id=workspace_id,
        limit=limit,
        force_recompute=force_recompute,
    )
    return SignalPriorityWorkspaceScoreResponse(
        workspace_id=workspace_id,
        requested_limit=limit,
        scored_count=len(scores),
        skipped_count=skipped_count,
        scores=[SignalPriorityScoreRead.model_validate(score) for score in scores],
    )
