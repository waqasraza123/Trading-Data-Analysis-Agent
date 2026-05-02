from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.decision_readiness.models import (
    DecisionReadinessLabel,
    DecisionReadinessSourceType,
)
from app.modules.decision_readiness.schemas import (
    DecisionReadinessAssessmentListResponse,
    DecisionReadinessAssessmentRequest,
    DecisionReadinessAssessmentResponse,
)
from app.modules.decision_readiness.service import DecisionReadinessService

router = APIRouter(prefix="/decision-readiness", tags=["decision-readiness"])


def get_decision_readiness_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> DecisionReadinessService:
    return DecisionReadinessService(session)


@router.post(
    "/signals/{signal_id}/assess",
    response_model=DecisionReadinessAssessmentResponse,
)
async def assess_signal_readiness(
    signal_id: UUID,
    request: DecisionReadinessAssessmentRequest,
    service: Annotated[
        DecisionReadinessService,
        Depends(get_decision_readiness_service),
    ],
) -> DecisionReadinessAssessmentResponse:
    return await service.assess_signal(
        signal_id,
        force_recompute=request.force_recompute,
    )


@router.get(
    "/signals/{signal_id}/latest",
    response_model=DecisionReadinessAssessmentResponse,
)
async def get_latest_signal_readiness(
    signal_id: UUID,
    service: Annotated[
        DecisionReadinessService,
        Depends(get_decision_readiness_service),
    ],
) -> DecisionReadinessAssessmentResponse:
    return await service.get_latest_for_signal(signal_id)


@router.post(
    "/analysis-runs/{analysis_run_id}/assess",
    response_model=DecisionReadinessAssessmentResponse,
)
async def assess_analysis_run_readiness(
    analysis_run_id: UUID,
    request: DecisionReadinessAssessmentRequest,
    service: Annotated[
        DecisionReadinessService,
        Depends(get_decision_readiness_service),
    ],
) -> DecisionReadinessAssessmentResponse:
    return await service.assess_analysis_run(
        analysis_run_id,
        force_recompute=request.force_recompute,
    )


@router.get(
    "/analysis-runs/{analysis_run_id}/latest",
    response_model=DecisionReadinessAssessmentResponse,
)
async def get_latest_analysis_run_readiness(
    analysis_run_id: UUID,
    service: Annotated[
        DecisionReadinessService,
        Depends(get_decision_readiness_service),
    ],
) -> DecisionReadinessAssessmentResponse:
    return await service.get_latest_for_analysis_run(analysis_run_id)


@router.get("", response_model=DecisionReadinessAssessmentListResponse)
async def list_decision_readiness_assessments(
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    service: Annotated[
        DecisionReadinessService,
        Depends(get_decision_readiness_service),
    ],
    readiness_label: Annotated[
        DecisionReadinessLabel | None,
        Query(alias="readinessLabel"),
    ] = None,
    source_type: Annotated[
        DecisionReadinessSourceType | None,
        Query(alias="sourceType"),
    ] = None,
    signal_id: Annotated[UUID | None, Query(alias="signalId")] = None,
    analysis_run_id: Annotated[UUID | None, Query(alias="analysisRunId")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DecisionReadinessAssessmentListResponse:
    return await service.list_assessments(
        workspace_id=workspace_id,
        limit=limit,
        offset=offset,
        readiness_label=readiness_label.value if readiness_label is not None else None,
        source_type=source_type.value if source_type is not None else None,
        signal_id=signal_id,
        analysis_run_id=analysis_run_id,
    )
