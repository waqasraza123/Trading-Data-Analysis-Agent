from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.intelligence_metrics.collector import CollectedMetrics, IntelligenceMetricCollector
from app.modules.intelligence_metrics.models import (
    IntelligenceMetricSnapshot,
    IntelligenceMetricSnapshotStatus,
    IntelligenceMetricSnapshotType,
)
from app.modules.intelligence_metrics.repository import IntelligenceMetricsRepository, utc_now


class IntelligenceMetricsService:
    def __init__(
        self,
        session: AsyncSession,
        repository: IntelligenceMetricsRepository | None = None,
        collector: IntelligenceMetricCollector | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or IntelligenceMetricsRepository(session)
        self.collector = collector or IntelligenceMetricCollector(self.repository)

    async def collect_workspace_metrics(self, workspace_id: UUID) -> CollectedMetrics:
        return await self.collector.collect_workspace_metrics(workspace_id)

    async def collect_global_metrics(self) -> CollectedMetrics:
        return await self.collector.collect_global_metrics()

    async def collect_module_metrics(
        self,
        module_name: str,
        workspace_id: UUID | None = None,
    ) -> CollectedMetrics:
        return await self.collector.collect_module_metrics(module_name, workspace_id)

    async def create_metric_snapshot(
        self,
        snapshot_type: IntelligenceMetricSnapshotType,
        workspace_id: UUID | None = None,
        module_name: str | None = None,
    ) -> IntelligenceMetricSnapshot:
        try:
            if snapshot_type == IntelligenceMetricSnapshotType.WORKSPACE:
                if workspace_id is None:
                    msg = "workspace_id is required for workspace metric snapshots"
                    raise ValueError(msg)
                collected = await self.collect_workspace_metrics(workspace_id)
            elif snapshot_type == IntelligenceMetricSnapshotType.GLOBAL:
                collected = await self.collect_global_metrics()
            elif snapshot_type == IntelligenceMetricSnapshotType.MODULE:
                if module_name is None:
                    msg = "module_name is required for module metric snapshots"
                    raise ValueError(msg)
                collected = await self.collect_module_metrics(module_name, workspace_id)
            elif snapshot_type == IntelligenceMetricSnapshotType.OPERATIONAL_HEALTH:
                collected = await self.collector.collect(
                    snapshot_type=IntelligenceMetricSnapshotType.OPERATIONAL_HEALTH,
                    workspace_id=workspace_id,
                )
            else:
                msg = "Unsupported intelligence metric snapshot type"
                raise ValueError(msg)
            snapshot = await self.repository.create_snapshot(
                workspace_id=workspace_id,
                snapshot_type=snapshot_type,
                status=collected.status,
                collected_at=collected.collected_at,
                metrics_json=collected.metrics_json,
                warnings_json=collected.warnings_json,
            )
            await self.session.commit()
            return snapshot
        except Exception as error:
            snapshot = await self.repository.create_snapshot(
                workspace_id=workspace_id,
                snapshot_type=snapshot_type,
                status=IntelligenceMetricSnapshotStatus.FAILED,
                collected_at=utc_now(),
                metrics_json={
                    "scope": {
                        "snapshotType": snapshot_type.value,
                        "workspaceId": str(workspace_id) if workspace_id is not None else None,
                        "moduleName": module_name,
                    },
                    "operationalHealth": {
                        "status": "failed",
                        "summary": "Backend intelligence metric collection failed.",
                    },
                },
                warnings_json=[
                    {
                        "moduleName": "intelligence_metrics",
                        "code": "metrics_collection_failed",
                        "message": str(error),
                    }
                ],
            )
            await self.session.commit()
            return snapshot

    async def get_latest_snapshot(
        self,
        workspace_id: UUID | None = None,
        snapshot_type: IntelligenceMetricSnapshotType | None = None,
    ) -> IntelligenceMetricSnapshot | None:
        return await self.repository.get_latest_snapshot(workspace_id, snapshot_type)

    async def list_snapshots(
        self,
        workspace_id: UUID | None = None,
        snapshot_type: IntelligenceMetricSnapshotType | None = None,
        status: IntelligenceMetricSnapshotStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IntelligenceMetricSnapshot]:
        return await self.repository.list_snapshots(
            workspace_id=workspace_id,
            snapshot_type=snapshot_type,
            status=status,
            limit=limit,
            offset=offset,
        )
