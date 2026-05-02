from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.context_packs.schemas import ContextPackOptions, ContextPackRead
from app.modules.context_packs.service import ContextPackService

router = APIRouter(prefix="/context-packs", tags=["context-packs"])


def get_context_pack_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ContextPackService:
    return ContextPackService(session, request.app.state.settings)


def context_pack_options(
    include_audit: Annotated[bool, Query(alias="includeAudit")] = True,
    include_reasoning: Annotated[bool, Query(alias="includeReasoning")] = True,
    include_actions: Annotated[bool, Query(alias="includeActions")] = True,
    include_outcomes: Annotated[bool, Query(alias="includeOutcomes")] = True,
    include_diagnostics: Annotated[bool, Query(alias="includeDiagnostics")] = True,
    include_quality: Annotated[bool, Query(alias="includeQuality")] = True,
    include_reports: Annotated[bool, Query(alias="includeReports")] = True,
    include_screenshots: Annotated[bool, Query(alias="includeScreenshots")] = True,
    max_evidence_rows: Annotated[int | None, Query(alias="maxEvidenceRows", ge=1, le=500)] = None,
    max_audit_events: Annotated[int | None, Query(alias="maxAuditEvents", ge=1, le=1000)] = None,
    max_outcomes: Annotated[int | None, Query(alias="maxOutcomes", ge=1, le=500)] = None,
) -> ContextPackOptions:
    return ContextPackOptions(
        include_audit=include_audit,
        include_reasoning=include_reasoning,
        include_actions=include_actions,
        include_outcomes=include_outcomes,
        include_diagnostics=include_diagnostics,
        include_quality=include_quality,
        include_reports=include_reports,
        include_screenshots=include_screenshots,
        max_evidence_rows=max_evidence_rows,
        max_audit_events=max_audit_events,
        max_outcomes=max_outcomes,
    )


@router.get("/signals/{signal_id}", response_model=ContextPackRead)
async def get_signal_context_pack(
    signal_id: UUID,
    service: Annotated[ContextPackService, Depends(get_context_pack_service)],
    options: Annotated[ContextPackOptions, Depends(context_pack_options)],
) -> ContextPackRead:
    return await service.build_for_signal(signal_id, options)


@router.get("/analysis-runs/{analysis_run_id}", response_model=ContextPackRead)
async def get_analysis_run_context_pack(
    analysis_run_id: UUID,
    service: Annotated[ContextPackService, Depends(get_context_pack_service)],
    options: Annotated[ContextPackOptions, Depends(context_pack_options)],
) -> ContextPackRead:
    return await service.build_for_analysis_run(analysis_run_id, options)


@router.get("/reasoning-runs/{reasoning_run_id}", response_model=ContextPackRead)
async def get_reasoning_run_context_pack(
    reasoning_run_id: UUID,
    service: Annotated[ContextPackService, Depends(get_context_pack_service)],
    options: Annotated[ContextPackOptions, Depends(context_pack_options)],
) -> ContextPackRead:
    return await service.build_for_reasoning_run(reasoning_run_id, options)


@router.get("/outcomes/{outcome_id}", response_model=ContextPackRead)
async def get_outcome_context_pack(
    outcome_id: UUID,
    service: Annotated[ContextPackService, Depends(get_context_pack_service)],
    options: Annotated[ContextPackOptions, Depends(context_pack_options)],
) -> ContextPackRead:
    return await service.build_for_outcome(outcome_id, options)


@router.get("/chart-screenshot-runs/{run_id}", response_model=ContextPackRead)
async def get_chart_screenshot_run_context_pack(
    run_id: UUID,
    service: Annotated[ContextPackService, Depends(get_context_pack_service)],
    options: Annotated[ContextPackOptions, Depends(context_pack_options)],
) -> ContextPackRead:
    return await service.build_for_chart_screenshot_run(run_id, options)
