from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.context_packs.builders import ContextPackBuilders
from app.modules.context_packs.limits import ContextPackLimits
from app.modules.context_packs.redaction import ContextPackRedactionState
from app.modules.context_packs.repository import ContextPackRepository
from app.modules.context_packs.schemas import (
    ContextPackOptions,
    ContextPackRead,
    ContextPackSubject,
    ContextPackSubjectType,
)


class ContextPackService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.repository = ContextPackRepository(session)
        self.settings = settings

    async def build_for_signal(
        self,
        signal_id: UUID,
        options: ContextPackOptions | None = None,
    ) -> ContextPackRead:
        resolved_options = options or ContextPackOptions()
        signal = await self.repository.get_signal(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        missing_sections: list[str] = []
        warnings = self.default_warnings()
        state = ContextPackRedactionState()
        limits = self.resolve_limits(resolved_options)
        sections = await self.builders(
            limits, resolved_options, state, missing_sections, warnings
        ).signal_sections(signal)
        return self.context_pack(
            subject_type=ContextPackSubjectType.SIGNAL,
            subject_id=signal.id,
            workspace_id=signal.workspace_id,
            sections=sections,
            missing_sections=missing_sections,
            warnings=warnings,
            state=state,
        )

    async def build_for_analysis_run(
        self,
        analysis_run_id: UUID,
        options: ContextPackOptions | None = None,
    ) -> ContextPackRead:
        resolved_options = options or ContextPackOptions()
        run = await self.repository.get_analysis_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        missing_sections: list[str] = []
        warnings = self.default_warnings()
        state = ContextPackRedactionState()
        limits = self.resolve_limits(resolved_options)
        sections = await self.builders(
            limits,
            resolved_options,
            state,
            missing_sections,
            warnings,
        ).analysis_run_sections(run)
        subject_type = (
            ContextPackSubjectType.REPLAY
            if run.analysis_mode == "replay"
            else ContextPackSubjectType.ANALYSIS_RUN
        )
        return self.context_pack(
            subject_type=subject_type,
            subject_id=run.id,
            workspace_id=run.workspace_id,
            sections=sections,
            missing_sections=missing_sections,
            warnings=warnings,
            state=state,
        )

    async def build_for_reasoning_run(
        self,
        reasoning_run_id: UUID,
        options: ContextPackOptions | None = None,
    ) -> ContextPackRead:
        resolved_options = options or ContextPackOptions()
        run = await self.repository.get_reasoning_run(reasoning_run_id)
        if run is None:
            raise AppError(404, "reasoning_run_not_found", "Reasoning run not found")
        missing_sections: list[str] = []
        warnings = self.default_warnings()
        state = ContextPackRedactionState()
        limits = self.resolve_limits(resolved_options)
        sections = await self.builders(
            limits,
            resolved_options,
            state,
            missing_sections,
            warnings,
        ).reasoning_run_sections(run)
        return self.context_pack(
            subject_type=ContextPackSubjectType.REASONING_RUN,
            subject_id=run.id,
            workspace_id=run.workspace_id,
            sections=sections,
            missing_sections=missing_sections,
            warnings=warnings,
            state=state,
        )

    async def build_for_outcome(
        self,
        outcome_id: UUID,
        options: ContextPackOptions | None = None,
    ) -> ContextPackRead:
        resolved_options = options or ContextPackOptions()
        outcome = await self.repository.get_outcome(outcome_id)
        if outcome is None:
            raise AppError(404, "outcome_not_found", "Outcome not found")
        missing_sections: list[str] = []
        warnings = self.default_warnings()
        state = ContextPackRedactionState()
        limits = self.resolve_limits(resolved_options)
        sections = await self.builders(
            limits,
            resolved_options,
            state,
            missing_sections,
            warnings,
        ).outcome_sections(outcome)
        return self.context_pack(
            subject_type=ContextPackSubjectType.OUTCOME,
            subject_id=outcome.id,
            workspace_id=outcome.workspace_id,
            sections=sections,
            missing_sections=missing_sections,
            warnings=warnings,
            state=state,
        )

    async def build_for_chart_screenshot_run(
        self,
        run_id: UUID,
        options: ContextPackOptions | None = None,
    ) -> ContextPackRead:
        resolved_options = options or ContextPackOptions()
        run = await self.repository.get_chart_screenshot_run(run_id)
        if run is None:
            raise AppError(
                404,
                "chart_screenshot_run_not_found",
                "Chart screenshot run not found",
            )
        missing_sections: list[str] = []
        warnings = self.default_warnings()
        state = ContextPackRedactionState()
        limits = self.resolve_limits(resolved_options)
        sections = await self.builders(
            limits,
            resolved_options,
            state,
            missing_sections,
            warnings,
        ).chart_screenshot_run_sections(run)
        return self.context_pack(
            subject_type=ContextPackSubjectType.CHART_SCREENSHOT_RUN,
            subject_id=run.id,
            workspace_id=run.workspace_id,
            sections=sections,
            missing_sections=missing_sections,
            warnings=warnings,
            state=state,
        )

    def builders(
        self,
        limits: ContextPackLimits,
        options: ContextPackOptions,
        state: ContextPackRedactionState,
        missing_sections: list[str],
        warnings: list[str],
    ) -> ContextPackBuilders:
        return ContextPackBuilders(
            repository=self.repository,
            limits=limits,
            options=options,
            state=state,
            missing_sections=missing_sections,
            warnings=warnings,
        )

    def resolve_limits(self, options: ContextPackOptions) -> ContextPackLimits:
        return ContextPackLimits.from_settings(self.settings).with_overrides(
            max_evidence_rows=options.max_evidence_rows,
            max_audit_events=options.max_audit_events,
            max_outcomes=options.max_outcomes,
        )

    def context_pack(
        self,
        subject_type: ContextPackSubjectType,
        subject_id: UUID,
        workspace_id: UUID,
        sections: dict[str, object],
        missing_sections: list[str],
        warnings: list[str],
        state: ContextPackRedactionState,
    ) -> ContextPackRead:
        return ContextPackRead(
            context_pack_version=self.settings.context_pack_schema_version,
            subject=ContextPackSubject(type=subject_type, id=subject_id),
            workspace_id=workspace_id,
            generated_at=utc_now(),
            sections=sections,
            missing_sections=sorted(set(missing_sections)),
            warnings=warnings,
            truncation=state.truncation_summary(),
            redaction=state.redaction_summary(),
        )

    def default_warnings(self) -> list[str]:
        return [
            "Context packs are read-only bounded artifact snapshots.",
            "Context packs do not execute actions, evaluate outcomes, call providers, "
            "or trigger LLM generation.",
            "Context packs are not financial advice and do not provide market-action instructions.",
        ]
