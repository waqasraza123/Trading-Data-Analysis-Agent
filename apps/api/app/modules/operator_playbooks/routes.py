from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.operator_playbooks.schemas import (
    OperatorPlaybookEvaluationRead,
    OperatorPlaybookEvaluationRequest,
    OperatorPlaybookRead,
)
from app.modules.operator_playbooks.service import OperatorPlaybookService

router = APIRouter(prefix="/operator-playbooks", tags=["operator-playbooks"])


def get_operator_playbook_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> OperatorPlaybookService:
    return OperatorPlaybookService(session)


@router.get("", response_model=list[OperatorPlaybookRead])
async def list_operator_playbooks(
    service: Annotated[OperatorPlaybookService, Depends(get_operator_playbook_service)],
) -> list[OperatorPlaybookRead]:
    return [OperatorPlaybookRead.model_validate(item) for item in await service.list_playbooks()]


@router.post("/seed", response_model=list[OperatorPlaybookRead])
async def seed_operator_playbooks(
    service: Annotated[OperatorPlaybookService, Depends(get_operator_playbook_service)],
) -> list[OperatorPlaybookRead]:
    return [OperatorPlaybookRead.model_validate(item) for item in await service.seed_playbooks()]


@router.post("/evaluate", response_model=OperatorPlaybookEvaluationRead)
async def evaluate_operator_playbooks(
    request: OperatorPlaybookEvaluationRequest,
    service: Annotated[OperatorPlaybookService, Depends(get_operator_playbook_service)],
) -> OperatorPlaybookEvaluationRead:
    return OperatorPlaybookEvaluationRead.model_validate(await service.evaluate(request))


@router.get("/evaluations", response_model=list[OperatorPlaybookEvaluationRead])
async def list_operator_playbook_evaluations(
    workspace_id: UUID,
    service: Annotated[OperatorPlaybookService, Depends(get_operator_playbook_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[OperatorPlaybookEvaluationRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    evaluations = await service.list_evaluations(workspace_id, pagination.limit, pagination.offset)
    return [OperatorPlaybookEvaluationRead.model_validate(item) for item in evaluations]


@router.get("/{key}", response_model=OperatorPlaybookRead)
async def get_operator_playbook(
    key: str,
    service: Annotated[OperatorPlaybookService, Depends(get_operator_playbook_service)],
) -> OperatorPlaybookRead:
    return OperatorPlaybookRead.model_validate(await service.get_playbook(key))
