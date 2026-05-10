from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.explanation_comparison.schemas import (
    ExplanationComparisonFindingRead,
    ExplanationComparisonRequest,
    ExplanationComparisonResponse,
)
from app.modules.explanation_comparison.service import ExplanationComparisonService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["explanation-comparison"])


def get_explanation_comparison_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ExplanationComparisonService:
    return ExplanationComparisonService(session)


@router.post(
    "/signals/{signal_id}/explanation-comparison",
    response_model=ExplanationComparisonResponse,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def compare_signal_explanations(
    signal_id: UUID,
    request: ExplanationComparisonRequest,
    service: Annotated[
        ExplanationComparisonService,
        Depends(get_explanation_comparison_service),
    ],
) -> ExplanationComparisonResponse:
    return await service.compare_signal_explanations(
        signal_id=signal_id,
        force_recompute=request.force_recompute,
    )


@router.get(
    "/signals/{signal_id}/explanation-comparison/latest",
    response_model=ExplanationComparisonResponse,
)
async def get_latest_signal_explanation_comparison(
    signal_id: UUID,
    service: Annotated[
        ExplanationComparisonService,
        Depends(get_explanation_comparison_service),
    ],
) -> ExplanationComparisonResponse:
    return await service.get_latest_for_signal(signal_id)


@router.get(
    "/explanation-comparisons/{run_id}",
    response_model=ExplanationComparisonResponse,
)
async def get_explanation_comparison(
    run_id: UUID,
    service: Annotated[
        ExplanationComparisonService,
        Depends(get_explanation_comparison_service),
    ],
) -> ExplanationComparisonResponse:
    return await service.get_comparison_run(run_id)


@router.get(
    "/explanation-comparisons/{run_id}/findings",
    response_model=list[ExplanationComparisonFindingRead],
)
async def list_explanation_comparison_findings(
    run_id: UUID,
    service: Annotated[
        ExplanationComparisonService,
        Depends(get_explanation_comparison_service),
    ],
) -> list[ExplanationComparisonFindingRead]:
    return await service.list_findings(run_id)
