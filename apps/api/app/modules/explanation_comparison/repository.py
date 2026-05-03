from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.explanation_comparison.models import (
    ExplanationComparisonFinding,
    ExplanationComparisonRun,
)
from app.modules.explanations.models import DeterministicExplanation
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.news.models import SignalNewsCorrelation
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.scenario_ensembles.models import ScenarioConsensusResult, ScenarioEnsembleRun
from app.modules.signals.models import Signal, SignalEvidence, SignalRiskNote


@dataclass
class ExplanationComparisonArtifacts:
    signal: Signal | None = None
    evidence: list[SignalEvidence] = field(default_factory=list)
    risk_notes: list[SignalRiskNote] = field(default_factory=list)
    deterministic_explanation: DeterministicExplanation | None = None
    llm_explanation: LlmExplanation | None = None
    reasoning_run: LlmReasoningRun | None = None
    scenarios: list[ScenarioHypothesis] = field(default_factory=list)
    news_correlations: list[SignalNewsCorrelation] = field(default_factory=list)
    scenario_ensemble_run: ScenarioEnsembleRun | None = None
    scenario_consensus: list[ScenarioConsensusResult] = field(default_factory=list)


class ExplanationComparisonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: ExplanationComparisonRun) -> ExplanationComparisonRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def create_findings(
        self,
        findings: list[ExplanationComparisonFinding],
    ) -> list[ExplanationComparisonFinding]:
        self.session.add_all(findings)
        await self.session.flush()
        for finding in findings:
            await self.session.refresh(finding)
        return findings

    async def get_run(self, run_id: UUID) -> ExplanationComparisonRun | None:
        return await self.session.get(ExplanationComparisonRun, run_id)

    async def get_latest_for_signal(
        self,
        signal_id: UUID,
        comparison_version: str,
    ) -> ExplanationComparisonRun | None:
        statement: Select[tuple[ExplanationComparisonRun]] = (
            select(ExplanationComparisonRun)
            .where(
                ExplanationComparisonRun.signal_id == signal_id,
                ExplanationComparisonRun.comparison_version == comparison_version,
            )
            .order_by(ExplanationComparisonRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_findings(
        self,
        comparison_run_id: UUID,
    ) -> list[ExplanationComparisonFinding]:
        statement: Select[tuple[ExplanationComparisonFinding]] = (
            select(ExplanationComparisonFinding)
            .where(ExplanationComparisonFinding.comparison_run_id == comparison_run_id)
            .order_by(
                ExplanationComparisonFinding.severity.desc(),
                ExplanationComparisonFinding.code.asc(),
                ExplanationComparisonFinding.created_at.asc(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def load_for_signal(self, signal_id: UUID) -> ExplanationComparisonArtifacts:
        signal = await self.session.get(Signal, signal_id)
        if signal is None:
            return ExplanationComparisonArtifacts()
        reasoning_run = await self.get_latest_reasoning_run(signal.id)
        ensemble_run = await self.get_latest_scenario_ensemble_run(signal.id)
        return ExplanationComparisonArtifacts(
            signal=signal,
            evidence=await self.list_evidence(signal.id),
            risk_notes=await self.list_risk_notes(signal.id),
            deterministic_explanation=await self.get_deterministic_explanation(signal.id),
            llm_explanation=await self.get_latest_llm_explanation(signal.id),
            reasoning_run=reasoning_run,
            scenarios=await self.list_scenarios(reasoning_run.id) if reasoning_run else [],
            news_correlations=await self.list_news_correlations(signal.id),
            scenario_ensemble_run=ensemble_run,
            scenario_consensus=(
                await self.list_scenario_consensus(ensemble_run.id) if ensemble_run else []
            ),
        )

    async def list_evidence(self, signal_id: UUID) -> list[SignalEvidence]:
        statement: Select[tuple[SignalEvidence]] = (
            select(SignalEvidence)
            .where(SignalEvidence.signal_id == signal_id)
            .order_by(SignalEvidence.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_risk_notes(self, signal_id: UUID) -> list[SignalRiskNote]:
        statement: Select[tuple[SignalRiskNote]] = (
            select(SignalRiskNote)
            .where(SignalRiskNote.signal_id == signal_id)
            .order_by(SignalRiskNote.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_deterministic_explanation(
        self,
        signal_id: UUID,
    ) -> DeterministicExplanation | None:
        statement: Select[tuple[DeterministicExplanation]] = select(
            DeterministicExplanation
        ).where(DeterministicExplanation.signal_id == signal_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_llm_explanation(self, signal_id: UUID) -> LlmExplanation | None:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(LlmExplanation.signal_id == signal_id)
            .order_by(LlmExplanation.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_reasoning_run(self, signal_id: UUID) -> LlmReasoningRun | None:
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(LlmReasoningRun.signal_id == signal_id)
            .order_by(LlmReasoningRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_scenarios(self, reasoning_run_id: UUID) -> list[ScenarioHypothesis]:
        statement: Select[tuple[ScenarioHypothesis]] = (
            select(ScenarioHypothesis)
            .where(ScenarioHypothesis.reasoning_run_id == reasoning_run_id)
            .order_by(ScenarioHypothesis.sort_order.asc(), ScenarioHypothesis.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_news_correlations(self, signal_id: UUID) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.signal_id == signal_id)
            .order_by(SignalNewsCorrelation.correlation_score.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_scenario_ensemble_run(
        self,
        signal_id: UUID,
    ) -> ScenarioEnsembleRun | None:
        statement: Select[tuple[ScenarioEnsembleRun]] = (
            select(ScenarioEnsembleRun)
            .where(ScenarioEnsembleRun.signal_id == signal_id)
            .order_by(ScenarioEnsembleRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_scenario_consensus(
        self,
        ensemble_run_id: UUID,
    ) -> list[ScenarioConsensusResult]:
        statement: Select[tuple[ScenarioConsensusResult]] = (
            select(ScenarioConsensusResult)
            .where(ScenarioConsensusResult.ensemble_run_id == ensemble_run_id)
            .order_by(ScenarioConsensusResult.agreement_count.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
