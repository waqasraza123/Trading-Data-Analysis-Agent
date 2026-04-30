from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_intelligence.models import AiIntelligenceSubjectType
from app.modules.ai_intelligence.schemas import AiArtifactRef, AiIntelligenceInputSnapshot
from app.modules.intelligence_reports.schemas import IntelligenceReportOptions
from app.modules.intelligence_reports.service import IntelligenceReportService

ARTIFACT_KEY_TYPES = {
    "signal_id": "signal",
    "analysis_run_id": "analysis_run",
    "reasoning_run_id": "reasoning_run",
    "outcome_id": "outcome",
    "news_event_id": "news_event",
    "action_plan_id": "reasoning_action_plan",
    "chart_screenshot_run_id": "chart_screenshot_run",
    "diagnostic_run_id": "strategy_profile_diagnostic_run",
    "symbol_id": "symbol",
    "source_id": "data_source",
}

SAFETY_RULES = [
    "AI intelligence is advisory and grounded in persisted backend artifacts.",
    "AI intelligence must not classify or override deterministic signals.",
    "AI intelligence must not invent prices, indicators, outcomes, news, or evidence.",
    "AI intelligence must not claim news causation.",
    "AI intelligence must not recommend buy, sell, enter, exit, order, leverage, "
    "or position actions.",
    "AI intelligence must not mutate strategy profiles or create executable action items.",
]


class AiIntelligenceInputBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self.report_service = IntelligenceReportService(session)

    async def build_signal_snapshot(self, signal_id: UUID) -> AiIntelligenceInputSnapshot:
        report = await self.report_service.build_signal_report(signal_id, report_options())
        signal_summary = report.sections.get("summary")
        analysis_run_id = value_uuid(signal_summary, "analysis_run_id")
        return AiIntelligenceInputSnapshot(
            subject_type=AiIntelligenceSubjectType.SIGNAL,
            subject_id=signal_id,
            workspace_id=report.workspace_id,
            signal_id=signal_id,
            analysis_run_id=analysis_run_id,
            outcome_id=None,
            report_type=report.report_type.value,
            artifact_refs=collect_artifact_refs(
                subject_type=AiIntelligenceSubjectType.SIGNAL.value,
                subject_id=signal_id,
                sections=report.sections,
            ),
            report_sections=report.sections,
            safety_rules=SAFETY_RULES,
        )


def report_options() -> IntelligenceReportOptions:
    return IntelligenceReportOptions(
        include_audit=True,
        include_reasoning=True,
        include_actions=True,
        include_outcomes=True,
        include_diagnostics=True,
        limit_audit=100,
        limit_evidence=50,
    )


def collect_artifact_refs(
    subject_type: str,
    subject_id: UUID,
    sections: dict[str, Any],
) -> list[AiArtifactRef]:
    refs: dict[tuple[str, str], AiArtifactRef] = {
        (subject_type, str(subject_id)): AiArtifactRef(
            artifact_type=subject_type,
            artifact_id=subject_id,
            label="report subject",
        )
    }
    collect_refs_from_value(sections, refs)
    return list(refs.values())


def collect_refs_from_value(
    value: object,
    refs: dict[tuple[str, str], AiArtifactRef],
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            artifact_type = ARTIFACT_KEY_TYPES.get(str(key))
            if artifact_type is not None:
                artifact_id = parse_uuid(item)
                if artifact_id is not None:
                    refs[(artifact_type, str(artifact_id))] = AiArtifactRef(
                        artifact_type=artifact_type,
                        artifact_id=artifact_id,
                        label=str(key),
                    )
            collect_refs_from_value(item, refs)
    elif isinstance(value, list):
        for item in value:
            collect_refs_from_value(item, refs)


def parse_uuid(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def value_uuid(value: object, key: str) -> UUID | None:
    if not isinstance(value, dict):
        return None
    return parse_uuid(value.get(key))
