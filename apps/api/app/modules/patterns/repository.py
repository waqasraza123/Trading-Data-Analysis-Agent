from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patterns.models import PatternCandidate


class PatternCandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_for_analysis_run(
        self,
        analysis_run_id: UUID,
        candidates: list[PatternCandidate],
    ) -> list[PatternCandidate]:
        await self.session.execute(
            delete(PatternCandidate).where(PatternCandidate.analysis_run_id == analysis_run_id)
        )
        self.session.add_all(candidates)
        await self.session.flush()
        for candidate in candidates:
            await self.session.refresh(candidate)
        return candidates

    async def list_by_analysis_run_id(self, analysis_run_id: UUID) -> list[PatternCandidate]:
        statement: Select[tuple[PatternCandidate]] = (
            select(PatternCandidate)
            .where(PatternCandidate.analysis_run_id == analysis_run_id)
            .order_by(
                PatternCandidate.is_selected.desc(),
                PatternCandidate.strength_score.desc(),
                PatternCandidate.created_at.desc(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
