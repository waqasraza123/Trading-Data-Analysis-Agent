from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.intelligence_reports.schemas import (
    IntelligenceReportOptions,
    IntelligenceReportRead,
)
from app.modules.intelligence_reports.service import IntelligenceReportService

router = APIRouter(prefix="/intelligence-reports", tags=["intelligence-reports"])


def get_intelligence_report_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> IntelligenceReportService:
    return IntelligenceReportService(session)


def report_options(
    include_audit: Annotated[bool, Query(alias="includeAudit")] = True,
    include_reasoning: Annotated[bool, Query(alias="includeReasoning")] = True,
    include_actions: Annotated[bool, Query(alias="includeActions")] = True,
    include_outcomes: Annotated[bool, Query(alias="includeOutcomes")] = True,
    include_diagnostics: Annotated[bool, Query(alias="includeDiagnostics")] = True,
    limit_audit: Annotated[int, Query(alias="limitAudit", ge=1, le=500)] = 100,
    limit_evidence: Annotated[int, Query(alias="limitEvidence", ge=1, le=500)] = 50,
) -> IntelligenceReportOptions:
    return IntelligenceReportOptions(
        include_audit=include_audit,
        include_reasoning=include_reasoning,
        include_actions=include_actions,
        include_outcomes=include_outcomes,
        include_diagnostics=include_diagnostics,
        limit_audit=limit_audit,
        limit_evidence=limit_evidence,
    )


@router.get("/signals/{signal_id}", response_model=IntelligenceReportRead)
async def get_signal_intelligence_report(
    signal_id: UUID,
    service: Annotated[IntelligenceReportService, Depends(get_intelligence_report_service)],
    options: Annotated[IntelligenceReportOptions, Depends(report_options)],
) -> IntelligenceReportRead:
    return await service.build_signal_report(signal_id, options)


@router.get("/analysis-runs/{analysis_run_id}", response_model=IntelligenceReportRead)
async def get_analysis_run_intelligence_report(
    analysis_run_id: UUID,
    service: Annotated[IntelligenceReportService, Depends(get_intelligence_report_service)],
    options: Annotated[IntelligenceReportOptions, Depends(report_options)],
) -> IntelligenceReportRead:
    return await service.build_analysis_run_report(analysis_run_id, options)


@router.get("/reasoning-runs/{reasoning_run_id}", response_model=IntelligenceReportRead)
async def get_reasoning_run_intelligence_report(
    reasoning_run_id: UUID,
    service: Annotated[IntelligenceReportService, Depends(get_intelligence_report_service)],
    options: Annotated[IntelligenceReportOptions, Depends(report_options)],
) -> IntelligenceReportRead:
    return await service.build_reasoning_run_report(reasoning_run_id, options)


@router.get("/outcomes/{outcome_id}", response_model=IntelligenceReportRead)
async def get_outcome_intelligence_report(
    outcome_id: UUID,
    service: Annotated[IntelligenceReportService, Depends(get_intelligence_report_service)],
    options: Annotated[IntelligenceReportOptions, Depends(report_options)],
) -> IntelligenceReportRead:
    return await service.build_outcome_report(outcome_id=outcome_id, options=options)


@router.get("/signals/{signal_id}/outcomes", response_model=IntelligenceReportRead)
async def get_signal_outcome_intelligence_report(
    signal_id: UUID,
    service: Annotated[IntelligenceReportService, Depends(get_intelligence_report_service)],
    options: Annotated[IntelligenceReportOptions, Depends(report_options)],
) -> IntelligenceReportRead:
    return await service.build_outcome_report(signal_id=signal_id, options=options)


@router.get("/screenshot-decisions/{decision_id}", response_model=IntelligenceReportRead)
async def get_screenshot_decision_intelligence_report(
    decision_id: UUID,
    service: Annotated[IntelligenceReportService, Depends(get_intelligence_report_service)],
    options: Annotated[IntelligenceReportOptions, Depends(report_options)],
) -> IntelligenceReportRead:
    return await service.build_screenshot_decision_report(decision_id, options)
