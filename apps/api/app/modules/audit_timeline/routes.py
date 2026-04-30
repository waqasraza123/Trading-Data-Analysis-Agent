from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.audit_timeline.schemas import AuditTimelineOptions, AuditTimelineRead
from app.modules.audit_timeline.service import AuditTimelineService

router = APIRouter(prefix="/audit-timeline", tags=["audit-timeline"])


def get_audit_timeline_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AuditTimelineService:
    return AuditTimelineService(session)


def timeline_options(
    include_audit: Annotated[bool, Query(alias="includeAudit")] = True,
    include_graph: Annotated[bool, Query(alias="includeGraph")] = True,
    include_artifacts: Annotated[bool, Query(alias="includeArtifacts")] = True,
    include_metadata: Annotated[bool, Query(alias="includeMetadata")] = True,
    limit_events: Annotated[int, Query(alias="limitEvents", ge=1, le=500)] = 200,
    limit_audit: Annotated[int, Query(alias="limitAudit", ge=1, le=500)] = 100,
    limit_artifacts: Annotated[int, Query(alias="limitArtifacts", ge=1, le=500)] = 200,
) -> AuditTimelineOptions:
    return AuditTimelineOptions(
        include_audit=include_audit,
        include_graph=include_graph,
        include_artifacts=include_artifacts,
        include_metadata=include_metadata,
        limit_events=limit_events,
        limit_audit=limit_audit,
        limit_artifacts=limit_artifacts,
    )


@router.get("/analysis-runs/{analysis_run_id}", response_model=AuditTimelineRead)
async def get_analysis_run_audit_timeline(
    analysis_run_id: UUID,
    service: Annotated[AuditTimelineService, Depends(get_audit_timeline_service)],
    options: Annotated[AuditTimelineOptions, Depends(timeline_options)],
) -> AuditTimelineRead:
    return await service.build_analysis_run_timeline(analysis_run_id, options)


@router.get("/signals/{signal_id}", response_model=AuditTimelineRead)
async def get_signal_audit_timeline(
    signal_id: UUID,
    service: Annotated[AuditTimelineService, Depends(get_audit_timeline_service)],
    options: Annotated[AuditTimelineOptions, Depends(timeline_options)],
) -> AuditTimelineRead:
    return await service.build_signal_timeline(signal_id, options)


@router.get("/reasoning-runs/{reasoning_run_id}", response_model=AuditTimelineRead)
async def get_reasoning_run_audit_timeline(
    reasoning_run_id: UUID,
    service: Annotated[AuditTimelineService, Depends(get_audit_timeline_service)],
    options: Annotated[AuditTimelineOptions, Depends(timeline_options)],
) -> AuditTimelineRead:
    return await service.build_reasoning_run_timeline(reasoning_run_id, options)


@router.get("/action-plans/{action_plan_id}", response_model=AuditTimelineRead)
async def get_action_plan_audit_timeline(
    action_plan_id: UUID,
    service: Annotated[AuditTimelineService, Depends(get_audit_timeline_service)],
    options: Annotated[AuditTimelineOptions, Depends(timeline_options)],
) -> AuditTimelineRead:
    return await service.build_action_plan_timeline(action_plan_id, options)


@router.get("/outcomes/{outcome_id}", response_model=AuditTimelineRead)
async def get_outcome_audit_timeline(
    outcome_id: UUID,
    service: Annotated[AuditTimelineService, Depends(get_audit_timeline_service)],
    options: Annotated[AuditTimelineOptions, Depends(timeline_options)],
) -> AuditTimelineRead:
    return await service.build_outcome_timeline(outcome_id, options)


@router.get("/chart-screenshot-runs/{run_id}", response_model=AuditTimelineRead)
async def get_chart_screenshot_run_audit_timeline(
    run_id: UUID,
    service: Annotated[AuditTimelineService, Depends(get_audit_timeline_service)],
    options: Annotated[AuditTimelineOptions, Depends(timeline_options)],
) -> AuditTimelineRead:
    return await service.build_chart_screenshot_run_timeline(run_id, options)
