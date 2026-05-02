from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.operator_reviews.models import (
    OperatorReviewPriority,
    OperatorReviewSourceType,
    OperatorReviewStatus,
    OperatorReviewType,
)
from app.modules.operator_reviews.schemas import (
    OperatorReviewAssignRequest,
    OperatorReviewCreateRequest,
    OperatorReviewDismissRequest,
    OperatorReviewEventRead,
    OperatorReviewItemRead,
    OperatorReviewResolveRequest,
    OperatorReviewStatusUpdateRequest,
)
from app.modules.operator_reviews.service import OperatorReviewService

router = APIRouter(prefix="/operator-reviews", tags=["operator-reviews"])


def get_operator_review_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> OperatorReviewService:
    return OperatorReviewService(session)


@router.post(
    "",
    response_model=OperatorReviewItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_operator_review_item(
    payload: OperatorReviewCreateRequest,
    service: Annotated[OperatorReviewService, Depends(get_operator_review_service)],
) -> OperatorReviewItemRead:
    return await service.create_review_item(payload)


@router.get("", response_model=list[OperatorReviewItemRead])
async def list_operator_review_items(
    service: Annotated[OperatorReviewService, Depends(get_operator_review_service)],
    workspace_id: UUID,
    item_status: Annotated[OperatorReviewStatus | None, Query(alias="status")] = None,
    priority: OperatorReviewPriority | None = None,
    review_type: OperatorReviewType | None = None,
    source_type: OperatorReviewSourceType | None = None,
    assigned_to_user_id: UUID | None = None,
    related_signal_id: UUID | None = None,
    related_analysis_run_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[OperatorReviewItemRead]:
    return await service.list_review_items(
        workspace_id=workspace_id,
        status=item_status,
        priority=priority,
        review_type=review_type,
        source_type=source_type,
        assigned_to_user_id=assigned_to_user_id,
        related_signal_id=related_signal_id,
        related_analysis_run_id=related_analysis_run_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{review_item_id}", response_model=OperatorReviewItemRead)
async def get_operator_review_item(
    review_item_id: UUID,
    service: Annotated[OperatorReviewService, Depends(get_operator_review_service)],
) -> OperatorReviewItemRead:
    return await service.get_review_item(review_item_id)


@router.post("/{review_item_id}/assign", response_model=OperatorReviewItemRead)
async def assign_operator_review_item(
    review_item_id: UUID,
    payload: OperatorReviewAssignRequest,
    service: Annotated[OperatorReviewService, Depends(get_operator_review_service)],
) -> OperatorReviewItemRead:
    return await service.assign_review_item(
        review_item_id=review_item_id,
        user_id=payload.user_id,
        actor_user_id=payload.actor_user_id,
    )


@router.post("/{review_item_id}/status", response_model=OperatorReviewItemRead)
async def update_operator_review_status(
    review_item_id: UUID,
    payload: OperatorReviewStatusUpdateRequest,
    service: Annotated[OperatorReviewService, Depends(get_operator_review_service)],
) -> OperatorReviewItemRead:
    return await service.update_review_status(
        review_item_id=review_item_id,
        status=payload.status,
        actor_user_id=payload.actor_user_id,
        notes=payload.notes,
    )


@router.post("/{review_item_id}/resolve", response_model=OperatorReviewItemRead)
async def resolve_operator_review_item(
    review_item_id: UUID,
    payload: OperatorReviewResolveRequest,
    service: Annotated[OperatorReviewService, Depends(get_operator_review_service)],
) -> OperatorReviewItemRead:
    return await service.resolve_review_item(
        review_item_id=review_item_id,
        resolution=payload.resolution,
        notes=payload.resolution_notes,
        reviewed_by_user_id=payload.reviewed_by_user_id,
    )


@router.post("/{review_item_id}/dismiss", response_model=OperatorReviewItemRead)
async def dismiss_operator_review_item(
    review_item_id: UUID,
    payload: OperatorReviewDismissRequest,
    service: Annotated[OperatorReviewService, Depends(get_operator_review_service)],
) -> OperatorReviewItemRead:
    return await service.dismiss_review_item(
        review_item_id=review_item_id,
        notes=payload.resolution_notes,
        reviewed_by_user_id=payload.reviewed_by_user_id,
    )


@router.get("/{review_item_id}/events", response_model=list[OperatorReviewEventRead])
async def list_operator_review_events(
    review_item_id: UUID,
    service: Annotated[OperatorReviewService, Depends(get_operator_review_service)],
) -> list[OperatorReviewEventRead]:
    return await service.list_review_events(review_item_id)
