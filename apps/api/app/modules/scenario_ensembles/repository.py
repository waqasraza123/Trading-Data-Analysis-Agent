from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scenario_ensembles.models import (
    ScenarioConsensusResult,
    ScenarioEnsembleItem,
    ScenarioEnsembleRun,
)


class ScenarioEnsembleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: ScenarioEnsembleRun) -> ScenarioEnsembleRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: ScenarioEnsembleRun) -> ScenarioEnsembleRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> ScenarioEnsembleRun | None:
        return await self.session.get(ScenarioEnsembleRun, run_id)

    async def get_latest_completed_for_request(
        self,
        signal_id: UUID,
        ensemble_version: str,
        providers: list[str],
        models: list[str],
    ) -> ScenarioEnsembleRun | None:
        statement: Select[tuple[ScenarioEnsembleRun]] = (
            select(ScenarioEnsembleRun)
            .where(
                ScenarioEnsembleRun.signal_id == signal_id,
                ScenarioEnsembleRun.ensemble_version == ensemble_version,
                ScenarioEnsembleRun.requested_providers_json == providers,
                ScenarioEnsembleRun.requested_models_json == models,
            )
            .order_by(ScenarioEnsembleRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_signal_runs(self, signal_id: UUID) -> list[ScenarioEnsembleRun]:
        statement: Select[tuple[ScenarioEnsembleRun]] = (
            select(ScenarioEnsembleRun)
            .where(ScenarioEnsembleRun.signal_id == signal_id)
            .order_by(ScenarioEnsembleRun.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_item(self, item: ScenarioEnsembleItem) -> ScenarioEnsembleItem:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def list_items(self, ensemble_run_id: UUID) -> list[ScenarioEnsembleItem]:
        statement: Select[tuple[ScenarioEnsembleItem]] = (
            select(ScenarioEnsembleItem)
            .where(ScenarioEnsembleItem.ensemble_run_id == ensemble_run_id)
            .order_by(ScenarioEnsembleItem.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def replace_consensus_results(
        self,
        ensemble_run_id: UUID,
        results: list[ScenarioConsensusResult],
    ) -> list[ScenarioConsensusResult]:
        await self.session.execute(
            delete(ScenarioConsensusResult).where(
                ScenarioConsensusResult.ensemble_run_id == ensemble_run_id
            )
        )
        self.session.add_all(results)
        await self.session.flush()
        for result in results:
            await self.session.refresh(result)
        return results

    async def list_consensus_results(
        self,
        ensemble_run_id: UUID,
    ) -> list[ScenarioConsensusResult]:
        statement: Select[tuple[ScenarioConsensusResult]] = (
            select(ScenarioConsensusResult)
            .where(ScenarioConsensusResult.ensemble_run_id == ensemble_run_id)
            .order_by(
                ScenarioConsensusResult.agreement_count.desc(),
                ScenarioConsensusResult.scenario_type.asc(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
