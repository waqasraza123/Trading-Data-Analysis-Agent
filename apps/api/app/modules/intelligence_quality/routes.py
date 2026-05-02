from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.intelligence_quality.schemas import (
    IntelligenceQualityFindingRead,
    IntelligenceQualityResponse,
    IntelligenceQualityRunRequest,
    ShadowClassificationResultRead,
)
from app.modules.intelligence_quality.service import IntelligenceQualityService

router = APIRouter(prefix="/intelligence-quality", tags=["intelligence-quality"])


def get_intelligence_quality_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> IntelligenceQualityService:
    return IntelligenceQualityService(session)


@router.post("/signals/{signal_id}/run", response_model=IntelligenceQualityResponse)
async def run_signal_quality(
    signal_id: UUID,
    payload: IntelligenceQualityRunRequest,
    service: Annotated[IntelligenceQualityService, Depends(get_intelligence_quality_service)],
) -> IntelligenceQualityResponse:
    return await service.run_for_signal(
        signal_id=signal_id,
        include_shadow_classification=payload.include_shadow_classification,
        force_recompute=payload.force_recompute,
    )


@router.get("/signals/{signal_id}/latest", response_model=IntelligenceQualityResponse)
async def get_latest_signal_quality(
    signal_id: UUID,
    service: Annotated[IntelligenceQualityService, Depends(get_intelligence_quality_service)],
) -> IntelligenceQualityResponse:
    return await service.get_latest_for_signal(signal_id)


@router.post("/analysis-runs/{analysis_run_id}/run", response_model=IntelligenceQualityResponse)
async def run_analysis_quality(
    analysis_run_id: UUID,
    payload: IntelligenceQualityRunRequest,
    service: Annotated[IntelligenceQualityService, Depends(get_intelligence_quality_service)],
) -> IntelligenceQualityResponse:
    return await service.run_for_analysis_run(
        analysis_run_id=analysis_run_id,
        include_shadow_classification=payload.include_shadow_classification,
        force_recompute=payload.force_recompute,
    )


@router.get("/analysis-runs/{analysis_run_id}/latest", response_model=IntelligenceQualityResponse)
async def get_latest_analysis_quality(
    analysis_run_id: UUID,
    service: Annotated[IntelligenceQualityService, Depends(get_intelligence_quality_service)],
) -> IntelligenceQualityResponse:
    return await service.get_latest_for_analysis_run(analysis_run_id)


@router.get("/runs/{quality_run_id}", response_model=IntelligenceQualityResponse)
async def get_quality_run(
    quality_run_id: UUID,
    service: Annotated[IntelligenceQualityService, Depends(get_intelligence_quality_service)],
) -> IntelligenceQualityResponse:
    return await service.response_for_run(quality_run_id)


@router.get(
    "/runs/{quality_run_id}/findings",
    response_model=list[IntelligenceQualityFindingRead],
)
async def list_quality_findings(
    quality_run_id: UUID,
    service: Annotated[IntelligenceQualityService, Depends(get_intelligence_quality_service)],
) -> list[IntelligenceQualityFindingRead]:
    return await service.list_findings(quality_run_id)


@router.get(
    "/runs/{quality_run_id}/shadow-classifications",
    response_model=list[ShadowClassificationResultRead],
)
async def list_shadow_classifications(
    quality_run_id: UUID,
    service: Annotated[IntelligenceQualityService, Depends(get_intelligence_quality_service)],
) -> list[ShadowClassificationResultRead]:
    return await service.list_shadow_classifications(quality_run_id)
