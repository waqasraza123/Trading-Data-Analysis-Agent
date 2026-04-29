from uuid import UUID

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.llm_explanations.models import LlmExplanation


class LlmExplanationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_signal_id(
        self,
        signal_id: UUID,
    ) -> LlmExplanation | None:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(LlmExplanation.signal_id == signal_id)
            .order_by(LlmExplanation.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_by_signal_provider_model(
        self,
        signal_id: UUID,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> LlmExplanation | None:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(
                and_(
                    LlmExplanation.signal_id == signal_id,
                    LlmExplanation.provider == provider,
                    LlmExplanation.model == model,
                    LlmExplanation.prompt_version == prompt_version,
                )
            )
            .order_by(LlmExplanation.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> LlmExplanation | None:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(LlmExplanation.analysis_run_id == analysis_run_id)
            .order_by(LlmExplanation.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def upsert_for_signal(self, explanation: LlmExplanation) -> LlmExplanation:
        existing = await self.get_by_signal_provider_model(
            signal_id=explanation.signal_id,
            provider=explanation.provider,
            model=explanation.model,
            prompt_version=explanation.prompt_version,
        )
        if existing is None:
            self.session.add(explanation)
            await self.session.flush()
            await self.session.refresh(explanation)
            return explanation
        existing.analysis_run_id = explanation.analysis_run_id
        existing.workspace_id = explanation.workspace_id
        existing.input_json = explanation.input_json
        existing.output_text = explanation.output_text
        existing.safety_status = explanation.safety_status
        existing.blocked_terms_json = explanation.blocked_terms_json
        existing.grounding_status = explanation.grounding_status
        existing.grounding_issues_json = explanation.grounding_issues_json
        existing.tokens_input = explanation.tokens_input
        existing.tokens_output = explanation.tokens_output
        existing.estimated_cost = explanation.estimated_cost
        existing.error_message = explanation.error_message
        await self.session.flush()
        await self.session.refresh(existing)
        return existing
