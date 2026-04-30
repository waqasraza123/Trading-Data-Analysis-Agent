from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reasoning.models import LlmReasoningRun, ReasoningRunStatus, ScenarioHypothesis


class ScenarioReasoningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: LlmReasoningRun) -> LlmReasoningRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> LlmReasoningRun | None:
        return await self.session.get(LlmReasoningRun, run_id)

    async def list_signal_runs(self, signal_id: UUID) -> list[LlmReasoningRun]:
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(LlmReasoningRun.signal_id == signal_id)
            .order_by(LlmReasoningRun.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_completed_signal_run(
        self,
        signal_id: UUID,
        reasoning_type: str,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> LlmReasoningRun | None:
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(
                LlmReasoningRun.signal_id == signal_id,
                LlmReasoningRun.reasoning_type == reasoning_type,
                LlmReasoningRun.provider == provider,
                LlmReasoningRun.model == model,
                LlmReasoningRun.prompt_version == prompt_version,
                LlmReasoningRun.status == ReasoningRunStatus.COMPLETED,
            )
            .order_by(LlmReasoningRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_signal_run(self, signal_id: UUID) -> LlmReasoningRun | None:
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(LlmReasoningRun.signal_id == signal_id)
            .order_by(LlmReasoningRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_run(self, run: LlmReasoningRun) -> LlmReasoningRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def replace_scenarios(
        self,
        reasoning_run_id: UUID,
        scenarios: list[ScenarioHypothesis],
    ) -> list[ScenarioHypothesis]:
        await self.session.execute(
            delete(ScenarioHypothesis).where(
                ScenarioHypothesis.reasoning_run_id == reasoning_run_id
            )
        )
        self.session.add_all(scenarios)
        await self.session.flush()
        for scenario in scenarios:
            await self.session.refresh(scenario)
        return scenarios

    async def list_scenarios(self, reasoning_run_id: UUID) -> list[ScenarioHypothesis]:
        statement: Select[tuple[ScenarioHypothesis]] = (
            select(ScenarioHypothesis)
            .where(ScenarioHypothesis.reasoning_run_id == reasoning_run_id)
            .order_by(ScenarioHypothesis.sort_order.asc(), ScenarioHypothesis.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
