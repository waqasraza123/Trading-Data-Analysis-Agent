from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advanced_features.models import AdvancedFeatureSnapshot


class AdvancedFeatureSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        feature_pack_version: str,
    ) -> AdvancedFeatureSnapshot | None:
        statement: Select[tuple[AdvancedFeatureSnapshot]] = select(AdvancedFeatureSnapshot).where(
            AdvancedFeatureSnapshot.analysis_run_id == analysis_run_id,
            AdvancedFeatureSnapshot.feature_pack_version == feature_pack_version,
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def upsert(
        self,
        snapshot: AdvancedFeatureSnapshot,
        existing: AdvancedFeatureSnapshot | None,
    ) -> AdvancedFeatureSnapshot:
        if existing is None:
            self.session.add(snapshot)
            await self.session.flush()
            await self.session.refresh(snapshot)
            return snapshot
        existing.workspace_id = snapshot.workspace_id
        existing.symbol_id = snapshot.symbol_id
        existing.timeframe = snapshot.timeframe
        existing.impulse_json = snapshot.impulse_json
        existing.correction_json = snapshot.correction_json
        existing.wick_pressure_json = snapshot.wick_pressure_json
        existing.movement_efficiency_json = snapshot.movement_efficiency_json
        existing.compression_expansion_json = snapshot.compression_expansion_json
        existing.swing_structure_json = snapshot.swing_structure_json
        existing.support_resistance_json = snapshot.support_resistance_json
        existing.exhaustion_json = snapshot.exhaustion_json
        existing.liquidity_sweep_json = snapshot.liquidity_sweep_json
        existing.warnings_json = snapshot.warnings_json
        existing.summary = snapshot.summary
        await self.session.flush()
        await self.session.refresh(existing)
        return existing
