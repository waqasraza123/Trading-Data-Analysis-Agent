from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog
from app.modules.analysis.repository import AnalysisRepository
from app.modules.outcomes.models import SignalOutcome
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.scenario_outcomes.evaluator import (
    ScenarioNewsContext,
    ScenarioOutcomeEvaluationInput,
    ScenarioOutcomeEvaluator,
)
from app.modules.scenario_outcomes.models import (
    ScenarioHypothesisOutcome,
    ScenarioOutcomeEvaluationStatus,
    ScenarioOutcomeSummaryRun,
    ScenarioOutcomeSummaryRunStatus,
    ScenarioOutcomeSupportLabel,
)
from app.modules.scenario_outcomes.repository import ScenarioOutcomeRepository
from app.modules.scenario_outcomes.schemas import (
    ReasoningRunScenarioOutcomesRead,
    ScenarioHypothesisOutcomeRead,
    ScenarioOutcomeSummaryRequest,
    ScenarioOutcomeSummaryRunRead,
    normalize_horizons,
)


class ScenarioOutcomeService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ScenarioOutcomeRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.evaluator = ScenarioOutcomeEvaluator()

    async def evaluate_scenario_hypothesis(
        self,
        scenario_hypothesis_id: UUID,
        horizon_minutes: int | None = None,
        force_recompute: bool = False,
    ) -> ScenarioHypothesisOutcomeRead:
        horizon = self.resolve_horizon(horizon_minutes)
        hypothesis = await self.load_hypothesis(scenario_hypothesis_id)
        existing = await self.repository.get_existing_hypothesis_outcome(
            scenario_hypothesis_id=hypothesis.id,
            horizon_minutes=horizon,
            evaluation_version=self.evaluation_version,
        )
        if existing is not None and not force_recompute:
            return ScenarioHypothesisOutcomeRead.model_validate(existing)
        reasoning_run = await self.load_reasoning_run(hypothesis.reasoning_run_id)
        outcome = await self.resolve_signal_outcome(hypothesis, reasoning_run, horizon)
        news_contexts = await self.news_contexts(hypothesis.signal_id)
        evaluation = self.evaluator.evaluate(
            ScenarioOutcomeEvaluationInput(
                scenario_type=hypothesis.scenario_type,
                scenario_label=hypothesis.scenario_label,
                possibility_label=hypothesis.possibility_label,
                outcome=outcome,
                news_contexts=news_contexts,
            ),
            support_threshold=self.support_threshold,
        )
        persisted = await self.repository.upsert_hypothesis_outcome(
            ScenarioHypothesisOutcome(
                workspace_id=hypothesis.workspace_id,
                scenario_hypothesis_id=hypothesis.id,
                reasoning_run_id=hypothesis.reasoning_run_id,
                signal_id=hypothesis.signal_id,
                analysis_run_id=hypothesis.analysis_run_id,
                outcome_id=outcome.id if outcome is not None else None,
                horizon_minutes=horizon,
                evaluation_version=self.evaluation_version,
                scenario_type=hypothesis.scenario_type,
                possibility_label=hypothesis.possibility_label,
                evaluation_status=evaluation.evaluation_status,
                support_label=evaluation.support_label,
                support_score=evaluation.support_score,
                matched_outcome_label=evaluation.matched_outcome_label,
                matched_evidence_json=evaluation.matched_evidence,
                conflicting_evidence_json=evaluation.conflicting_evidence,
                summary=evaluation.summary,
            ),
            force_recompute=force_recompute,
        )
        await self.add_audit_log(
            hypothesis=hypothesis,
            event_type="scenario_outcome_evaluation_completed",
            message="Scenario hypothesis outcome evaluation completed",
            metadata_json={
                "scenarioHypothesisId": str(hypothesis.id),
                "reasoningRunId": str(hypothesis.reasoning_run_id),
                "horizonMinutes": horizon,
                "supportLabel": persisted.support_label,
                "evaluationStatus": persisted.evaluation_status,
            },
        )
        await self.session.commit()
        return ScenarioHypothesisOutcomeRead.model_validate(persisted)

    async def evaluate_reasoning_run(
        self,
        reasoning_run_id: UUID,
        horizons_minutes: list[int] | None = None,
        force_recompute: bool = False,
    ) -> ReasoningRunScenarioOutcomesRead:
        await self.load_reasoning_run(reasoning_run_id)
        horizons = self.resolve_horizons(horizons_minutes)
        hypotheses = await self.repository.list_reasoning_hypotheses(reasoning_run_id)
        outcomes: list[ScenarioHypothesisOutcomeRead] = []
        for hypothesis in hypotheses:
            for horizon in horizons:
                outcome = await self.evaluate_scenario_hypothesis(
                    scenario_hypothesis_id=hypothesis.id,
                    horizon_minutes=horizon,
                    force_recompute=force_recompute,
                )
                outcomes.append(outcome)
        return ReasoningRunScenarioOutcomesRead(
            reasoning_run_id=reasoning_run_id, outcomes=outcomes
        )

    async def get_hypothesis_outcomes(
        self,
        reasoning_run_id: UUID,
    ) -> ReasoningRunScenarioOutcomesRead:
        await self.load_reasoning_run(reasoning_run_id)
        outcomes = await self.repository.list_hypothesis_outcomes(reasoning_run_id)
        return ReasoningRunScenarioOutcomesRead(
            reasoning_run_id=reasoning_run_id,
            outcomes=[
                ScenarioHypothesisOutcomeRead.model_validate(outcome) for outcome in outcomes
            ],
        )

    async def summarize_scenario_outcomes(
        self,
        payload: ScenarioOutcomeSummaryRequest,
    ) -> ScenarioOutcomeSummaryRunRead:
        run = await self.repository.create_summary_run(
            ScenarioOutcomeSummaryRun(
                workspace_id=payload.workspace_id,
                status=ScenarioOutcomeSummaryRunStatus.PENDING,
                summary_version=self.evaluation_version,
                filters_json=payload.filters.model_dump(mode="json"),
                summary="Scenario outcome summary is pending.",
            )
        )
        try:
            outcomes = await self.repository.list_summary_outcomes(
                workspace_id=payload.workspace_id,
                filters=payload.filters,
            )
            counts = support_counts(outcomes)
            run.evaluated_count = sum(
                1
                for outcome in outcomes
                if outcome.evaluation_status == ScenarioOutcomeEvaluationStatus.EVALUATED
            )
            run.supported_count = counts[ScenarioOutcomeSupportLabel.SUPPORTED]
            run.partially_supported_count = counts[ScenarioOutcomeSupportLabel.PARTIALLY_SUPPORTED]
            run.contradicted_count = counts[ScenarioOutcomeSupportLabel.CONTRADICTED]
            run.inconclusive_count = counts[ScenarioOutcomeSupportLabel.INCONCLUSIVE]
            run.status = (
                ScenarioOutcomeSummaryRunStatus.COMPLETED
                if outcomes
                else ScenarioOutcomeSummaryRunStatus.COMPLETED_WITH_WARNINGS
            )
            run.summary = scenario_summary_text(
                evaluated_count=run.evaluated_count,
                supported_count=run.supported_count,
                partially_supported_count=run.partially_supported_count,
                contradicted_count=run.contradicted_count,
                inconclusive_count=run.inconclusive_count,
            )
            await self.session.commit()
            await self.session.refresh(run)
            return ScenarioOutcomeSummaryRunRead.model_validate(run)
        except Exception as error:
            run.status = ScenarioOutcomeSummaryRunStatus.FAILED
            run.summary = f"Scenario outcome summary failed: {error}"
            await self.session.commit()
            await self.session.refresh(run)
            return ScenarioOutcomeSummaryRunRead.model_validate(run)

    async def get_summary_run(self, summary_run_id: UUID) -> ScenarioOutcomeSummaryRunRead:
        run = await self.repository.get_summary_run(summary_run_id)
        if run is None:
            raise AppError(
                404,
                "scenario_outcome_summary_run_not_found",
                "Scenario outcome summary run not found",
            )
        return ScenarioOutcomeSummaryRunRead.model_validate(run)

    async def load_hypothesis(self, scenario_hypothesis_id: UUID) -> ScenarioHypothesis:
        hypothesis = await self.repository.get_hypothesis(scenario_hypothesis_id)
        if hypothesis is None:
            raise AppError(
                404,
                "scenario_hypothesis_not_found",
                "Scenario hypothesis not found",
            )
        return hypothesis

    async def load_reasoning_run(self, reasoning_run_id: UUID) -> LlmReasoningRun:
        reasoning_run = await self.repository.get_reasoning_run(reasoning_run_id)
        if reasoning_run is None:
            raise AppError(404, "reasoning_run_not_found", "Reasoning run not found")
        return reasoning_run

    async def resolve_signal_outcome(
        self,
        hypothesis: ScenarioHypothesis,
        reasoning_run: LlmReasoningRun,
        horizon_minutes: int,
    ) -> SignalOutcome | None:
        if hypothesis.signal_id is not None:
            return await self.repository.get_signal_outcome_by_horizon(
                signal_id=hypothesis.signal_id,
                horizon_minutes=horizon_minutes,
            )
        if reasoning_run.outcome_id is None:
            return None
        outcome = await self.repository.get_signal_outcome_by_id(reasoning_run.outcome_id)
        if outcome is None or outcome.horizon_minutes != horizon_minutes:
            return None
        return outcome

    async def news_contexts(self, signal_id: UUID | None) -> list[ScenarioNewsContext]:
        if signal_id is None:
            return []
        correlations = await self.repository.list_news_contexts(signal_id)
        return [
            ScenarioNewsContext(
                correlation_label=correlation.correlation_label,
                volatility_reaction=correlation.volatility_reaction,
            )
            for correlation in correlations
        ]

    async def add_audit_log(
        self,
        hypothesis: ScenarioHypothesis,
        event_type: str,
        message: str,
        metadata_json: dict[str, object],
    ) -> None:
        if hypothesis.analysis_run_id is None:
            return
        await self.analysis_repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=hypothesis.analysis_run_id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )

    def resolve_horizon(self, horizon_minutes: int | None) -> int:
        return horizon_minutes or self.settings.scenario_outcome_default_horizon_minutes

    def resolve_horizons(self, horizons_minutes: list[int] | None) -> list[int]:
        if horizons_minutes is not None:
            return normalize_horizons(horizons_minutes)
        return [self.settings.scenario_outcome_default_horizon_minutes]

    @property
    def evaluation_version(self) -> str:
        return self.settings.scenario_outcome_evaluation_version

    @property
    def support_threshold(self) -> Decimal:
        return self.settings.scenario_outcome_support_threshold


def support_counts(
    outcomes: list[ScenarioHypothesisOutcome],
) -> dict[ScenarioOutcomeSupportLabel, int]:
    counts = {
        ScenarioOutcomeSupportLabel.SUPPORTED: 0,
        ScenarioOutcomeSupportLabel.PARTIALLY_SUPPORTED: 0,
        ScenarioOutcomeSupportLabel.CONTRADICTED: 0,
        ScenarioOutcomeSupportLabel.INCONCLUSIVE: 0,
        ScenarioOutcomeSupportLabel.NOT_APPLICABLE: 0,
    }
    for outcome in outcomes:
        counts[ScenarioOutcomeSupportLabel(outcome.support_label)] += 1
    return counts


def scenario_summary_text(
    evaluated_count: int,
    supported_count: int,
    partially_supported_count: int,
    contradicted_count: int,
    inconclusive_count: int,
) -> str:
    if evaluated_count == 0:
        return "No evaluated scenario hypothesis outcomes matched the requested filters."
    return (
        f"Summarized {evaluated_count} evaluated scenario hypothesis outcomes: "
        f"{supported_count} supported, {partially_supported_count} partially supported, "
        f"{contradicted_count} contradicted, and {inconclusive_count} inconclusive."
    )
