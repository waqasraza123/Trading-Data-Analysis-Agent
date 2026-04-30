from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_intelligence.models import (
    AiIntelligenceClaim,
    AiIntelligenceInsight,
    AiIntelligenceRun,
)


class AiIntelligenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: AiIntelligenceRun) -> AiIntelligenceRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: AiIntelligenceRun) -> AiIntelligenceRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> AiIntelligenceRun | None:
        return await self.session.get(AiIntelligenceRun, run_id)

    async def get_latest_completed_signal_run(
        self,
        signal_id: UUID,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> AiIntelligenceRun | None:
        statement: Select[tuple[AiIntelligenceRun]] = (
            select(AiIntelligenceRun)
            .where(
                AiIntelligenceRun.signal_id == signal_id,
                AiIntelligenceRun.provider == provider,
                AiIntelligenceRun.model == model,
                AiIntelligenceRun.prompt_version == prompt_version,
                AiIntelligenceRun.status.in_(["completed", "fallback_used"]),
            )
            .order_by(AiIntelligenceRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_signal_runs(
        self,
        signal_id: UUID,
        limit: int,
        offset: int,
    ) -> list[AiIntelligenceRun]:
        statement: Select[tuple[AiIntelligenceRun]] = (
            select(AiIntelligenceRun)
            .where(AiIntelligenceRun.signal_id == signal_id)
            .order_by(AiIntelligenceRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def replace_insights(
        self,
        run_id: UUID,
        insights: list[AiIntelligenceInsight],
    ) -> list[AiIntelligenceInsight]:
        await self.session.execute(
            delete(AiIntelligenceClaim).where(AiIntelligenceClaim.run_id == run_id)
        )
        await self.session.execute(
            delete(AiIntelligenceInsight).where(AiIntelligenceInsight.run_id == run_id)
        )
        self.session.add_all(insights)
        await self.session.flush()
        return insights

    async def create_claims(
        self,
        claims: list[AiIntelligenceClaim],
    ) -> list[AiIntelligenceClaim]:
        self.session.add_all(claims)
        await self.session.flush()
        return claims

    async def list_insights(self, run_id: UUID) -> list[AiIntelligenceInsight]:
        statement: Select[tuple[AiIntelligenceInsight]] = (
            select(AiIntelligenceInsight)
            .where(AiIntelligenceInsight.run_id == run_id)
            .order_by(AiIntelligenceInsight.sort_order.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_claims(self, run_id: UUID) -> list[AiIntelligenceClaim]:
        statement: Select[tuple[AiIntelligenceClaim]] = (
            select(AiIntelligenceClaim)
            .where(AiIntelligenceClaim.run_id == run_id)
            .order_by(AiIntelligenceClaim.sort_order.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
