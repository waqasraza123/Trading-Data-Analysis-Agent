from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.intelligence_metrics.collector import CollectedMetrics
from app.modules.intelligence_metrics.models import (
    IntelligenceMetricSnapshotStatus,
    IntelligenceMetricSnapshotType,
)
from app.modules.intelligence_metrics.schemas import (
    IntelligenceMetricSnapshotRead,
    IntelligenceMetricsRead,
    IntelligenceMetricWarning,
)
from app.modules.intelligence_metrics.service import IntelligenceMetricsService

router = APIRouter(prefix="/intelligence-metrics", tags=["intelligence-metrics"])


def get_intelligence_metrics_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> IntelligenceMetricsService:
    return IntelligenceMetricsService(session)


@router.get("/workspace/{workspace_id}", response_model=IntelligenceMetricsRead)
async def get_workspace_intelligence_metrics(
    workspace_id: UUID,
    service: Annotated[
        IntelligenceMetricsService,
        Depends(get_intelligence_metrics_service),
    ],
) -> IntelligenceMetricsRead:
    collected = await service.collect_workspace_metrics(workspace_id)
    return to_metrics_read(collected, workspace_id=workspace_id)


@router.get("/global", response_model=IntelligenceMetricsRead)
async def get_global_intelligence_metrics(
    service: Annotated[
        IntelligenceMetricsService,
        Depends(get_intelligence_metrics_service),
    ],
) -> IntelligenceMetricsRead:
    collected = await service.collect_global_metrics()
    return to_metrics_read(collected, workspace_id=None)


@router.post(
    "/snapshots/workspace/{workspace_id}",
    response_model=IntelligenceMetricSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_intelligence_metric_snapshot(
    workspace_id: UUID,
    service: Annotated[
        IntelligenceMetricsService,
        Depends(get_intelligence_metrics_service),
    ],
) -> IntelligenceMetricSnapshotRead:
    snapshot = await service.create_metric_snapshot(
        IntelligenceMetricSnapshotType.WORKSPACE,
        workspace_id=workspace_id,
    )
    return IntelligenceMetricSnapshotRead.model_validate(snapshot)


@router.post(
    "/snapshots/global",
    response_model=IntelligenceMetricSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_global_intelligence_metric_snapshot(
    service: Annotated[
        IntelligenceMetricsService,
        Depends(get_intelligence_metrics_service),
    ],
) -> IntelligenceMetricSnapshotRead:
    snapshot = await service.create_metric_snapshot(IntelligenceMetricSnapshotType.GLOBAL)
    return IntelligenceMetricSnapshotRead.model_validate(snapshot)


@router.get("/snapshots/latest", response_model=IntelligenceMetricSnapshotRead | None)
async def get_latest_intelligence_metric_snapshot(
    service: Annotated[
        IntelligenceMetricsService,
        Depends(get_intelligence_metrics_service),
    ],
    workspace_id: UUID | None = None,
    snapshot_type: IntelligenceMetricSnapshotType | None = None,
) -> IntelligenceMetricSnapshotRead | None:
    snapshot = await service.get_latest_snapshot(
        workspace_id=workspace_id,
        snapshot_type=snapshot_type,
    )
    return IntelligenceMetricSnapshotRead.model_validate(snapshot) if snapshot is not None else None


@router.get("/snapshots", response_model=list[IntelligenceMetricSnapshotRead])
async def list_intelligence_metric_snapshots(
    service: Annotated[
        IntelligenceMetricsService,
        Depends(get_intelligence_metrics_service),
    ],
    workspace_id: UUID | None = None,
    snapshot_type: IntelligenceMetricSnapshotType | None = None,
    snapshot_status: Annotated[
        IntelligenceMetricSnapshotStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IntelligenceMetricSnapshotRead]:
    snapshots = await service.list_snapshots(
        workspace_id=workspace_id,
        snapshot_type=snapshot_type,
        status=snapshot_status,
        limit=limit,
        offset=offset,
    )
    return [IntelligenceMetricSnapshotRead.model_validate(snapshot) for snapshot in snapshots]


def to_metrics_read(
    collected: CollectedMetrics,
    workspace_id: UUID | None,
    module_name: str | None = None,
) -> IntelligenceMetricsRead:
    health_summary = collected.metrics_json.get("operationalHealth", {})
    return IntelligenceMetricsRead(
        workspace_id=workspace_id,
        module_name=module_name,
        snapshot_type=collected.snapshot_type,
        status=collected.status,
        collected_at=collected.collected_at,
        metrics_json=collected.metrics_json,
        warnings_json=[
            IntelligenceMetricWarning.model_validate(warning)
            for warning in collected.warnings_json
        ],
        health_summary=health_summary if isinstance(health_summary, dict) else {},
    )
