from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.profile_governance.models import StrategyProfileDraftStatus
from app.modules.profile_governance.schemas import (
    StrategyProfileDraftCreate,
    StrategyProfileDraftEventRead,
    StrategyProfileDraftPromotionRequest,
    StrategyProfileDraftRead,
    StrategyProfileDraftUpdate,
    StrategyProfileDraftWorkflowRequest,
)
from app.modules.profile_governance.service import StrategyProfileGovernanceService

router = APIRouter(prefix="/strategy-profile-drafts", tags=["strategy-profile-drafts"])


def get_strategy_profile_governance_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> StrategyProfileGovernanceService:
    return StrategyProfileGovernanceService(session)


@router.post(
    "",
    response_model=StrategyProfileDraftRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.STRATEGY_PROFILES_ADMIN))],
)
async def create_strategy_profile_draft(
    payload: StrategyProfileDraftCreate,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> StrategyProfileDraftRead:
    draft = await service.create_draft(payload)
    return StrategyProfileDraftRead.model_validate(draft)


@router.get("", response_model=list[StrategyProfileDraftRead])
async def list_strategy_profile_drafts(
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
    workspace_id: UUID | None = None,
    status: StrategyProfileDraftStatus | None = None,
    draft_key: str | None = None,
    base_strategy_profile_key: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[StrategyProfileDraftRead]:
    drafts = await service.list_drafts(
        limit=limit,
        offset=offset,
        workspace_id=workspace_id,
        status=status,
        draft_key=draft_key,
        base_strategy_profile_key=base_strategy_profile_key,
    )
    return [StrategyProfileDraftRead.model_validate(draft) for draft in drafts]


@router.get("/{draft_id}", response_model=StrategyProfileDraftRead)
async def get_strategy_profile_draft(
    draft_id: UUID,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> StrategyProfileDraftRead:
    draft = await service.get_draft(draft_id)
    return StrategyProfileDraftRead.model_validate(draft)


@router.patch(
    "/{draft_id}",
    response_model=StrategyProfileDraftRead,
    dependencies=[Depends(require_permission(Permission.STRATEGY_PROFILES_ADMIN))],
)
async def update_strategy_profile_draft(
    draft_id: UUID,
    payload: StrategyProfileDraftUpdate,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> StrategyProfileDraftRead:
    draft = await service.update_draft(draft_id, payload)
    return StrategyProfileDraftRead.model_validate(draft)


@router.post(
    "/{draft_id}/validate",
    response_model=StrategyProfileDraftRead,
    dependencies=[Depends(require_permission(Permission.STRATEGY_PROFILES_ADMIN))],
)
async def validate_strategy_profile_draft(
    draft_id: UUID,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> StrategyProfileDraftRead:
    draft = await service.validate_draft(draft_id)
    return StrategyProfileDraftRead.model_validate(draft)


@router.post(
    "/{draft_id}/submit",
    response_model=StrategyProfileDraftRead,
    dependencies=[Depends(require_permission(Permission.STRATEGY_PROFILES_ADMIN))],
)
async def submit_strategy_profile_draft(
    draft_id: UUID,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> StrategyProfileDraftRead:
    draft = await service.submit_for_review(draft_id)
    return StrategyProfileDraftRead.model_validate(draft)


@router.post(
    "/{draft_id}/approve",
    response_model=StrategyProfileDraftRead,
    dependencies=[Depends(require_permission(Permission.STRATEGY_PROFILES_ADMIN))],
)
async def approve_strategy_profile_draft(
    draft_id: UUID,
    payload: StrategyProfileDraftWorkflowRequest,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> StrategyProfileDraftRead:
    draft = await service.approve_draft(draft_id, payload)
    return StrategyProfileDraftRead.model_validate(draft)


@router.post(
    "/{draft_id}/reject",
    response_model=StrategyProfileDraftRead,
    dependencies=[Depends(require_permission(Permission.STRATEGY_PROFILES_ADMIN))],
)
async def reject_strategy_profile_draft(
    draft_id: UUID,
    payload: StrategyProfileDraftWorkflowRequest,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> StrategyProfileDraftRead:
    draft = await service.reject_draft(draft_id, payload)
    return StrategyProfileDraftRead.model_validate(draft)


@router.post(
    "/{draft_id}/promote",
    response_model=StrategyProfileDraftRead,
    dependencies=[Depends(require_permission(Permission.STRATEGY_PROFILES_ADMIN))],
)
async def promote_strategy_profile_draft(
    draft_id: UUID,
    payload: StrategyProfileDraftPromotionRequest,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> StrategyProfileDraftRead:
    draft = await service.promote_draft(draft_id, payload)
    return StrategyProfileDraftRead.model_validate(draft)


@router.post(
    "/{draft_id}/archive",
    response_model=StrategyProfileDraftRead,
    dependencies=[Depends(require_permission(Permission.STRATEGY_PROFILES_ADMIN))],
)
async def archive_strategy_profile_draft(
    draft_id: UUID,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> StrategyProfileDraftRead:
    draft = await service.archive_draft(draft_id)
    return StrategyProfileDraftRead.model_validate(draft)


@router.get("/{draft_id}/events", response_model=list[StrategyProfileDraftEventRead])
async def list_strategy_profile_draft_events(
    draft_id: UUID,
    service: Annotated[
        StrategyProfileGovernanceService,
        Depends(get_strategy_profile_governance_service),
    ],
) -> list[StrategyProfileDraftEventRead]:
    events = await service.list_events(draft_id)
    return [StrategyProfileDraftEventRead.model_validate(event) for event in events]
