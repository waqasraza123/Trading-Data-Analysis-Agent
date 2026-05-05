from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.candles.timeframes import Timeframe
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.provider_health.models import (
    ProviderHealthFreshnessLabel,
    ProviderHealthStatus,
)
from app.modules.provider_health.schemas import (
    ProviderHealthPrepareGapRecoveryRequest,
    ProviderHealthPrepareGapRecoveryResponse,
    ProviderHealthSnapshotBuildRequest,
    ProviderHealthSnapshotListFilters,
    ProviderHealthSnapshotRead,
    ProviderHealthSummary,
    ProviderHealthWorkspaceRefreshResponse,
)
from app.modules.provider_health.service import ProviderHealthService

router = APIRouter(prefix="/provider-health", tags=["provider-health"])


def get_provider_health_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ProviderHealthService:
    return ProviderHealthService(session=session, settings=request.app.state.settings)


@router.post(
    "/snapshots",
    response_model=ProviderHealthSnapshotRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def build_provider_health_snapshot(
    payload: ProviderHealthSnapshotBuildRequest,
    service: Annotated[ProviderHealthService, Depends(get_provider_health_service)],
) -> ProviderHealthSnapshotRead:
    snapshot = await service.build_health_snapshot(
        workspace_id=payload.workspace_id,
        source_id=payload.source_id,
        symbol_id=payload.symbol_id,
        timeframe=payload.timeframe.value if payload.timeframe is not None else None,
        force_recompute=payload.force_recompute,
    )
    return ProviderHealthSnapshotRead.model_validate(snapshot)


@router.get("/snapshots", response_model=list[ProviderHealthSnapshotRead])
async def list_provider_health_snapshots(
    service: Annotated[ProviderHealthService, Depends(get_provider_health_service)],
    workspace_id: UUID,
    source_id: UUID | None = None,
    symbol_id: UUID | None = None,
    timeframe: Timeframe | None = None,
    provider: str | None = None,
    health_status: Annotated[ProviderHealthStatus | None, Query(alias="status")] = None,
    freshness_label: ProviderHealthFreshnessLabel | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ProviderHealthSnapshotRead]:
    snapshots = await service.list_health_snapshots(
        ProviderHealthSnapshotListFilters(
            workspace_id=workspace_id,
            source_id=source_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            provider=provider,
            status=health_status,
            freshness_label=freshness_label,
            limit=limit,
            offset=offset,
        )
    )
    return [ProviderHealthSnapshotRead.model_validate(snapshot) for snapshot in snapshots]


@router.get("/workspaces/{workspace_id}/summary", response_model=ProviderHealthSummary)
async def summarize_provider_health(
    workspace_id: UUID,
    service: Annotated[ProviderHealthService, Depends(get_provider_health_service)],
) -> ProviderHealthSummary:
    return await service.summarize_provider_health(workspace_id)


@router.post(
    "/workspaces/{workspace_id}/refresh",
    response_model=ProviderHealthWorkspaceRefreshResponse,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def refresh_provider_health_workspace(
    workspace_id: UUID,
    service: Annotated[ProviderHealthService, Depends(get_provider_health_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 500,
) -> ProviderHealthWorkspaceRefreshResponse:
    snapshots, skipped_count = await service.build_workspace_health(workspace_id, limit=limit)
    return ProviderHealthWorkspaceRefreshResponse(
        workspace_id=workspace_id,
        requested_limit=limit,
        refreshed_count=len(snapshots),
        skipped_count=skipped_count,
        snapshots=[
            ProviderHealthSnapshotRead.model_validate(snapshot) for snapshot in snapshots
        ],
    )


@router.post(
    "/snapshots/{snapshot_id}/prepare-gap-recovery",
    response_model=ProviderHealthPrepareGapRecoveryResponse,
    dependencies=[Depends(require_permission(Permission.PROVIDER_POLLING_WRITE))],
)
async def prepare_provider_health_gap_recovery(
    snapshot_id: UUID,
    payload: ProviderHealthPrepareGapRecoveryRequest,
    service: Annotated[ProviderHealthService, Depends(get_provider_health_service)],
) -> ProviderHealthPrepareGapRecoveryResponse:
    return await service.prepare_gap_recovery(
        snapshot_id=snapshot_id,
        create_requests=payload.create_requests,
    )
