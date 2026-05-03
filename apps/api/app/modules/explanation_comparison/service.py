from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.explanation_comparison.comparator import (
    ComparisonFindingDraft,
    ExplanationComparator,
)
from app.modules.explanation_comparison.models import (
    ExplanationComparisonFinding,
    ExplanationComparisonRun,
    ExplanationComparisonRunStatus,
)
from app.modules.explanation_comparison.repository import (
    ExplanationComparisonRepository,
)
from app.modules.explanation_comparison.schemas import (
    ExplanationComparisonFindingRead,
    ExplanationComparisonResponse,
    ExplanationComparisonRunRead,
)


class ExplanationComparisonService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ExplanationComparisonRepository(session)
        self.comparator = ExplanationComparator()

    async def compare_signal_explanations(
        self,
        signal_id: UUID,
        force_recompute: bool = False,
    ) -> ExplanationComparisonResponse:
        if not force_recompute:
            existing = await self.repository.get_latest_for_signal(
                signal_id=signal_id,
                comparison_version=self.settings.explanation_comparison_version,
            )
            if existing is not None:
                return await self.response_for_run(existing.id)
        artifacts = await self.repository.load_for_signal(signal_id)
        if artifacts.signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        try:
            result = self.comparator.compare(
                artifacts=artifacts,
                alignment_threshold=self.settings.explanation_comparison_alignment_threshold,
                review_threshold=self.settings.explanation_comparison_review_threshold,
            )
            run = await self.repository.create_run(
                ExplanationComparisonRun(
                    workspace_id=artifacts.signal.workspace_id,
                    signal_id=artifacts.signal.id,
                    analysis_run_id=artifacts.signal.analysis_run_id,
                    status=status_for_findings(result.findings),
                    comparison_version=self.settings.explanation_comparison_version,
                    deterministic_explanation_id=(
                        artifacts.deterministic_explanation.id
                        if artifacts.deterministic_explanation is not None
                        else None
                    ),
                    llm_explanation_id=(
                        artifacts.llm_explanation.id
                        if artifacts.llm_explanation is not None
                        else None
                    ),
                    reasoning_run_id=(
                        artifacts.reasoning_run.id if artifacts.reasoning_run is not None else None
                    ),
                    alignment_score=result.alignment_score,
                    alignment_label=result.alignment_label,
                    summary=result.summary,
                    metadata_json=result.metadata_json,
                )
            )
            persisted_findings = await self.repository.create_findings(
                [
                    finding_model(
                        workspace_id=artifacts.signal.workspace_id,
                        comparison_run_id=run.id,
                        draft=draft,
                    )
                    for draft in result.findings
                ]
            )
            await self.session.commit()
            return ExplanationComparisonResponse(
                comparison_run=ExplanationComparisonRunRead.model_validate(run),
                findings=[
                    ExplanationComparisonFindingRead.model_validate(item)
                    for item in persisted_findings
                ],
            )
        except Exception:
            await self.session.rollback()
            raise

    async def get_latest_for_signal(self, signal_id: UUID) -> ExplanationComparisonResponse:
        run = await self.repository.get_latest_for_signal(
            signal_id=signal_id,
            comparison_version=self.settings.explanation_comparison_version,
        )
        if run is None:
            raise AppError(
                404,
                "explanation_comparison_not_found",
                "Explanation comparison run not found",
            )
        return await self.response_for_run(run.id)

    async def get_comparison_run(self, run_id: UUID) -> ExplanationComparisonResponse:
        return await self.response_for_run(run_id)

    async def list_findings(self, run_id: UUID) -> list[ExplanationComparisonFindingRead]:
        await self.ensure_run(run_id)
        findings = await self.repository.list_findings(run_id)
        return [ExplanationComparisonFindingRead.model_validate(item) for item in findings]

    async def response_for_run(self, run_id: UUID) -> ExplanationComparisonResponse:
        run = await self.ensure_run(run_id)
        findings = await self.repository.list_findings(run.id)
        return ExplanationComparisonResponse(
            comparison_run=ExplanationComparisonRunRead.model_validate(run),
            findings=[ExplanationComparisonFindingRead.model_validate(item) for item in findings],
        )

    async def ensure_run(self, run_id: UUID) -> ExplanationComparisonRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(
                404,
                "explanation_comparison_not_found",
                "Explanation comparison run not found",
            )
        return run


def status_for_findings(findings: list[ComparisonFindingDraft]) -> str:
    if any(finding.severity == "critical" for finding in findings):
        return ExplanationComparisonRunStatus.COMPLETED_WITH_WARNINGS.value
    if findings:
        return ExplanationComparisonRunStatus.COMPLETED_WITH_WARNINGS.value
    return ExplanationComparisonRunStatus.COMPLETED.value


def finding_model(
    workspace_id: UUID,
    comparison_run_id: UUID,
    draft: ComparisonFindingDraft,
) -> ExplanationComparisonFinding:
    return ExplanationComparisonFinding(
        workspace_id=workspace_id,
        comparison_run_id=comparison_run_id,
        finding_type=draft.finding_type,
        severity=draft.severity,
        code=draft.code,
        message=draft.message,
        source_reference=draft.source_reference,
        metadata_json=draft.metadata_json,
    )
