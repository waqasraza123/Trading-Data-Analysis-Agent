from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candles.models import Candle
from app.modules.daily_workflows.models import DailyWorkflowRun
from app.modules.data_quality.models import DataQualityFinding, DataQualityRun
from app.modules.data_sources.models import DataSource
from app.modules.engine_versions.models import EngineVersion
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_scans.models import (
    MarketWatchlist,
    MarketWatchlistItem,
    ScheduledScanConfig,
)
from app.modules.notifications.models import (
    NotificationDeliveryChannel,
    NotificationWorkerRun,
)
from app.modules.product_readiness.models import ProductReadinessRun
from app.modules.provider_health.models import ProviderHealthSnapshot
from app.modules.scanner_presets.models import ScannerPreset
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.symbols.models import Symbol
from app.modules.trading_journal.models import JournalEntry
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace


class ProductReadinessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: ProductReadinessRun) -> ProductReadinessRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> ProductReadinessRun | None:
        return await self.session.get(ProductReadinessRun, run_id)

    async def get_latest(self, workspace_id: UUID | None = None) -> ProductReadinessRun | None:
        statement: Select[tuple[ProductReadinessRun]] = (
            select(ProductReadinessRun).order_by(ProductReadinessRun.created_at.desc()).limit(1)
        )
        if workspace_id is None:
            statement = statement.where(ProductReadinessRun.workspace_id.is_(None))
        else:
            statement = statement.where(ProductReadinessRun.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_runs(
        self,
        workspace_id: UUID | None,
        limit: int,
        offset: int,
        readiness_label: str | None = None,
        status: str | None = None,
    ) -> list[ProductReadinessRun]:
        statement: Select[tuple[ProductReadinessRun]] = (
            select(ProductReadinessRun)
            .order_by(ProductReadinessRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is None:
            statement = statement.where(ProductReadinessRun.workspace_id.is_(None))
        else:
            statement = statement.where(ProductReadinessRun.workspace_id == workspace_id)
        if readiness_label is not None:
            statement = statement.where(ProductReadinessRun.readiness_label == readiness_label)
        if status is not None:
            statement = statement.where(ProductReadinessRun.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def check_database_connection(self) -> bool:
        result = await self.session.execute(text("SELECT 1"))
        return int(result.scalar_one()) == 1

    async def get_alembic_versions(self) -> tuple[list[str], bool]:
        try:
            result = await self.session.execute(text("SELECT version_num FROM alembic_version"))
        except SQLAlchemyError:
            return [], False
        return sorted(str(row[0]) for row in result.all()), True

    async def get_workspace(self, workspace_id: UUID | None) -> Workspace | None:
        if workspace_id is not None:
            return await self.session.get(Workspace, workspace_id)
        statement = select(Workspace).order_by(Workspace.created_at.desc()).limit(1)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def count_workspaces(self) -> int:
        return await self.scalar_count(select(func.count()).select_from(Workspace))

    async def count_users(self, workspace_id: UUID | None) -> int:
        return await self.count_by_workspace(User, workspace_id)

    async def count_active_symbols(self) -> int:
        return await self.scalar_count(
            select(func.count()).select_from(Symbol).where(Symbol.is_active.is_(True))
        )

    async def count_active_data_sources(self, workspace_id: UUID | None) -> int:
        conditions = [DataSource.status == "active"]
        if workspace_id is not None:
            conditions.append(DataSource.workspace_id == workspace_id)
        return await self.scalar_count(
            select(func.count()).select_from(DataSource).where(and_(*conditions))
        )

    async def count_seed_records(self, workspace_id: UUID | None) -> dict[str, int]:
        return {
            "symbols": await self.scalar_count(select(func.count()).select_from(Symbol)),
            "data_sources": await self.count_by_workspace(DataSource, workspace_id),
            "strategy_profiles": await self.scalar_count(
                select(func.count()).select_from(StrategyProfile)
            ),
            "engine_versions": await self.scalar_count(
                select(func.count()).select_from(EngineVersion)
            ),
            "scanner_presets": await self.scalar_count(
                select(func.count()).select_from(ScannerPreset)
            ),
        }

    async def count_final_candles(self, workspace_id: UUID | None) -> int:
        conditions = [Candle.is_final.is_(True)]
        if workspace_id is not None:
            conditions.append(Candle.workspace_id == workspace_id)
        return await self.scalar_count(
            select(func.count()).select_from(Candle).where(and_(*conditions))
        )

    async def get_latest_final_candle_time(self, workspace_id: UUID | None) -> datetime | None:
        statement = select(func.max(Candle.timestamp)).where(Candle.is_final.is_(True))
        if workspace_id is not None:
            statement = statement.where(Candle.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        value = result.scalar_one()
        return value if isinstance(value, datetime) else None

    async def count_provider_health_snapshots(self, workspace_id: UUID | None) -> int:
        return await self.count_by_workspace(ProviderHealthSnapshot, workspace_id)

    async def provider_health_status_counts(self, workspace_id: UUID | None) -> dict[str, int]:
        statement = select(ProviderHealthSnapshot.status, func.count()).group_by(
            ProviderHealthSnapshot.status
        )
        if workspace_id is not None:
            statement = statement.where(ProviderHealthSnapshot.workspace_id == workspace_id)
        return await self.counts_by_key(statement)

    async def provider_health_freshness_counts(self, workspace_id: UUID | None) -> dict[str, int]:
        statement = select(ProviderHealthSnapshot.freshness_label, func.count()).group_by(
            ProviderHealthSnapshot.freshness_label
        )
        if workspace_id is not None:
            statement = statement.where(ProviderHealthSnapshot.workspace_id == workspace_id)
        return await self.counts_by_key(statement)

    async def count_active_watchlists(self, workspace_id: UUID | None) -> int:
        conditions = [MarketWatchlist.status == "active"]
        if workspace_id is not None:
            conditions.append(MarketWatchlist.workspace_id == workspace_id)
        return await self.scalar_count(
            select(func.count()).select_from(MarketWatchlist).where(and_(*conditions))
        )

    async def count_active_watchlist_items(self, workspace_id: UUID | None) -> int:
        conditions = [MarketWatchlistItem.is_active.is_(True)]
        if workspace_id is not None:
            conditions.append(MarketWatchlistItem.workspace_id == workspace_id)
        return await self.scalar_count(
            select(func.count()).select_from(MarketWatchlistItem).where(and_(*conditions))
        )

    async def count_active_scan_configs(self, workspace_id: UUID | None) -> int:
        conditions = [ScheduledScanConfig.status == "active"]
        if workspace_id is not None:
            conditions.append(ScheduledScanConfig.workspace_id == workspace_id)
        return await self.scalar_count(
            select(func.count()).select_from(ScheduledScanConfig).where(and_(*conditions))
        )

    async def count_daily_workflow_runs(self, workspace_id: UUID | None) -> int:
        return await self.count_by_workspace(DailyWorkflowRun, workspace_id)

    async def latest_daily_workflow_status(self, workspace_id: UUID | None) -> str | None:
        statement = select(DailyWorkflowRun.status).order_by(DailyWorkflowRun.created_at.desc())
        if workspace_id is not None:
            statement = statement.where(DailyWorkflowRun.workspace_id == workspace_id)
        result = await self.session.execute(statement.limit(1))
        value = result.scalar_one_or_none()
        return str(value) if value is not None else None

    async def count_notification_channels(self, workspace_id: UUID | None) -> int:
        conditions = [NotificationDeliveryChannel.status == "active"]
        if workspace_id is not None:
            conditions.append(NotificationDeliveryChannel.workspace_id == workspace_id)
        return await self.scalar_count(
            select(func.count()).select_from(NotificationDeliveryChannel).where(and_(*conditions))
        )

    async def count_notification_worker_runs(self, workspace_id: UUID | None) -> int:
        return await self.count_by_workspace(NotificationWorkerRun, workspace_id)

    async def count_journal_entries(self, workspace_id: UUID | None) -> int:
        return await self.count_by_workspace(JournalEntry, workspace_id)

    async def market_memory_freshness_counts(self, workspace_id: UUID | None) -> dict[str, int]:
        statement = select(RollingMarketStateSnapshot.freshness_label, func.count()).group_by(
            RollingMarketStateSnapshot.freshness_label
        )
        if workspace_id is not None:
            statement = statement.where(RollingMarketStateSnapshot.workspace_id == workspace_id)
        return await self.counts_by_key(statement)

    async def market_memory_quality_counts(self, workspace_id: UUID | None) -> dict[str, int]:
        statement = select(RollingMarketStateSnapshot.data_quality_label, func.count()).group_by(
            RollingMarketStateSnapshot.data_quality_label
        )
        if workspace_id is not None:
            statement = statement.where(RollingMarketStateSnapshot.workspace_id == workspace_id)
        return await self.counts_by_key(statement)

    async def data_quality_finding_counts(self, workspace_id: UUID | None) -> dict[str, int]:
        statement = select(DataQualityFinding.severity, func.count()).group_by(
            DataQualityFinding.severity
        )
        if workspace_id is not None:
            statement = statement.where(DataQualityFinding.workspace_id == workspace_id)
        return await self.counts_by_key(statement)

    async def count_data_quality_runs(self, workspace_id: UUID | None) -> int:
        return await self.count_by_workspace(DataQualityRun, workspace_id)

    async def count_by_workspace(self, model: type[object], workspace_id: UUID | None) -> int:
        statement = select(func.count()).select_from(model)
        if workspace_id is not None:
            statement = statement.where(model.workspace_id == workspace_id)
        return await self.scalar_count(statement)

    async def scalar_count(self, statement: Select[tuple[int]]) -> int:
        result = await self.session.execute(statement)
        value = result.scalar_one()
        return int(value or 0)

    async def counts_by_key(self, statement: Select[tuple[str, int]]) -> dict[str, int]:
        result = await self.session.execute(statement)
        return {str(key): int(count) for key, count in result.all()}
