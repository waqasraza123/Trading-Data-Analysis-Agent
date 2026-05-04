from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.market_memory.builder import MarketMemoryBuilder
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_memory.repository import MarketMemoryRepository
from app.modules.market_memory.schemas import MarketMemorySnapshotListFilters
from app.modules.symbols.repository import SymbolRepository


class MarketMemoryService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = MarketMemoryRepository(session)
        self.builder = MarketMemoryBuilder(self.repository, self.settings)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def build_state_snapshot(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None = None,
        force_recompute: bool = False,
    ) -> RollingMarketStateSnapshot:
        await self.validate_identity(workspace_id, symbol_id, source_id)
        existing = await self.repository.get_snapshot(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe,
            state_version=self.settings.market_memory_state_version,
        )
        snapshot = await self.builder.build(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe,
        )
        if (
            existing is not None
            and not force_recompute
            and snapshot_matches_existing(snapshot, existing)
        ):
            return existing
        try:
            persisted = await self.repository.upsert_snapshot(snapshot, existing)
            await self.session.commit()
            await self.session.refresh(persisted)
            return persisted
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "market_memory_snapshot_conflict",
                "Rolling market state snapshot could not be persisted",
            ) from error

    async def get_state_snapshot(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None = None,
    ) -> RollingMarketStateSnapshot:
        await self.validate_identity(workspace_id, symbol_id, source_id)
        snapshot = await self.repository.get_snapshot(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe,
            state_version=self.settings.market_memory_state_version,
        )
        if snapshot is None:
            raise AppError(
                404,
                "market_memory_snapshot_not_found",
                "Rolling market state snapshot not found",
            )
        return snapshot

    async def list_state_snapshots(
        self,
        filters: MarketMemorySnapshotListFilters,
    ) -> list[RollingMarketStateSnapshot]:
        return await self.repository.list_snapshots(
            workspace_id=filters.workspace_id,
            symbol_id=filters.symbol_id,
            source_id=filters.source_id,
            timeframe=filters.timeframe.value if filters.timeframe is not None else None,
            freshness_label=(
                filters.freshness_label.value if filters.freshness_label is not None else None
            ),
            data_quality_label=(
                filters.data_quality_label.value
                if filters.data_quality_label is not None
                else None
            ),
            limit=filters.limit,
            offset=filters.offset,
        )

    async def refresh_workspace_snapshots(
        self,
        workspace_id: UUID,
        limit: int = 500,
    ) -> tuple[list[RollingMarketStateSnapshot], int]:
        candidates = await self.repository.list_refresh_candidates(workspace_id, limit)
        snapshots: list[RollingMarketStateSnapshot] = []
        skipped_count = 0
        for candidate in candidates:
            try:
                snapshot = await self.build_state_snapshot(
                    workspace_id=candidate.workspace_id,
                    symbol_id=candidate.symbol_id,
                    source_id=candidate.source_id,
                    timeframe=candidate.timeframe,
                    force_recompute=False,
                )
            except AppError:
                skipped_count += 1
                continue
            snapshots.append(snapshot)
        return snapshots, skipped_count

    async def validate_identity(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
    ) -> None:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if source_id is None:
            return
        data_source = await self.data_source_repository.get_by_id(source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if data_source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )


def snapshot_matches_existing(
    snapshot: RollingMarketStateSnapshot,
    existing: RollingMarketStateSnapshot,
) -> bool:
    return (
        existing.latest_final_candle_time == snapshot.latest_final_candle_time
        and existing.latest_analysis_run_id == snapshot.latest_analysis_run_id
        and existing.latest_signal_id == snapshot.latest_signal_id
        and existing.latest_outcome_id == snapshot.latest_outcome_id
        and existing.data_quality_label == snapshot.data_quality_label
        and existing.freshness_label == snapshot.freshness_label
        and existing.context_json == snapshot.context_json
        and existing.warnings_json == snapshot.warnings_json
    )
