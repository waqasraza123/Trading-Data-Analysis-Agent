from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.explanations.models import DeterministicExplanation


class DeterministicExplanationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_signal_id(self, signal_id: UUID) -> DeterministicExplanation | None:
        statement: Select[tuple[DeterministicExplanation]] = select(DeterministicExplanation).where(
            DeterministicExplanation.signal_id == signal_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> DeterministicExplanation | None:
        statement: Select[tuple[DeterministicExplanation]] = (
            select(DeterministicExplanation)
            .where(DeterministicExplanation.analysis_run_id == analysis_run_id)
            .order_by(DeterministicExplanation.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def upsert_for_signal(
        self,
        explanation: DeterministicExplanation,
    ) -> DeterministicExplanation:
        existing = await self.get_by_signal_id(explanation.signal_id)
        if existing is None:
            self.session.add(explanation)
            await self.session.flush()
            await self.session.refresh(explanation)
            return explanation
        existing.analysis_run_id = explanation.analysis_run_id
        existing.workspace_id = explanation.workspace_id
        existing.template_version = explanation.template_version
        existing.explanation_type = explanation.explanation_type
        existing.short_summary = explanation.short_summary
        existing.market_behavior = explanation.market_behavior
        existing.evidence_summary = explanation.evidence_summary
        existing.confidence_summary = explanation.confidence_summary
        existing.risk_summary = explanation.risk_summary
        existing.no_signal_summary = explanation.no_signal_summary
        existing.full_text = explanation.full_text
        existing.source_snapshot_json = explanation.source_snapshot_json
        existing.safety_status = explanation.safety_status
        existing.blocked_terms_json = explanation.blocked_terms_json
        await self.session.flush()
        await self.session.refresh(existing)
        return existing
