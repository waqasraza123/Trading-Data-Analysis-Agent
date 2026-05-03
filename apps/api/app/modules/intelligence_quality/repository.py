from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.explanations.models import DeterministicExplanation
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFinding,
    IntelligenceQualityRun,
    ShadowClassificationResult,
)
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.news.models import SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.strategy_profiles.models import StrategyProfile


@dataclass
class IntelligenceQualityArtifacts:
    analysis_run: AnalysisRun | None = None
    signal: Signal | None = None
    feature_snapshot: FeatureSnapshot | None = None
    indicator_snapshot: IndicatorSnapshot | None = None
    pattern_candidates: list[PatternCandidate] = field(default_factory=list)
    confidence_components: list[SignalConfidenceComponent] = field(default_factory=list)
    evidence: list[SignalEvidence] = field(default_factory=list)
    risk_notes: list[SignalRiskNote] = field(default_factory=list)
    deterministic_explanation: DeterministicExplanation | None = None
    news_correlations: list[SignalNewsCorrelation] = field(default_factory=list)
    llm_explanation: LlmExplanation | None = None
    reasoning_runs: list[LlmReasoningRun] = field(default_factory=list)
    scenario_hypotheses: list[ScenarioHypothesis] = field(default_factory=list)
    outcomes: list[SignalOutcome] = field(default_factory=list)
    chart_screenshot_runs: list[ChartScreenshotRun] = field(default_factory=list)


class IntelligenceQualityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_run(self, quality_run_id: UUID) -> IntelligenceQualityRun | None:
        return await self.session.get(IntelligenceQualityRun, quality_run_id)

    async def get_latest_signal_run(
        self,
        signal_id: UUID,
        gate_version: str,
        shadow_version: str,
    ) -> IntelligenceQualityRun | None:
        statement: Select[tuple[IntelligenceQualityRun]] = (
            select(IntelligenceQualityRun)
            .where(
                IntelligenceQualityRun.signal_id == signal_id,
                IntelligenceQualityRun.gate_version == gate_version,
                IntelligenceQualityRun.shadow_version == shadow_version,
            )
            .order_by(IntelligenceQualityRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_analysis_run(
        self,
        analysis_run_id: UUID,
        gate_version: str,
        shadow_version: str,
    ) -> IntelligenceQualityRun | None:
        statement: Select[tuple[IntelligenceQualityRun]] = (
            select(IntelligenceQualityRun)
            .where(
                IntelligenceQualityRun.analysis_run_id == analysis_run_id,
                IntelligenceQualityRun.gate_version == gate_version,
                IntelligenceQualityRun.shadow_version == shadow_version,
            )
            .order_by(IntelligenceQualityRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_quality_run(
        self,
        run: IntelligenceQualityRun,
    ) -> IntelligenceQualityRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def create_findings(
        self,
        findings: list[IntelligenceQualityFinding],
    ) -> list[IntelligenceQualityFinding]:
        self.session.add_all(findings)
        await self.session.flush()
        for finding in findings:
            await self.session.refresh(finding)
        return findings

    async def create_shadow_results(
        self,
        results: list[ShadowClassificationResult],
    ) -> list[ShadowClassificationResult]:
        self.session.add_all(results)
        await self.session.flush()
        for result in results:
            await self.session.refresh(result)
        return results

    async def list_findings(
        self,
        quality_run_id: UUID,
    ) -> list[IntelligenceQualityFinding]:
        statement: Select[tuple[IntelligenceQualityFinding]] = (
            select(IntelligenceQualityFinding)
            .where(IntelligenceQualityFinding.quality_run_id == quality_run_id)
            .order_by(
                IntelligenceQualityFinding.severity.desc(),
                IntelligenceQualityFinding.created_at.asc(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_shadow_results(
        self,
        quality_run_id: UUID,
    ) -> list[ShadowClassificationResult]:
        statement: Select[tuple[ShadowClassificationResult]] = (
            select(ShadowClassificationResult)
            .where(ShadowClassificationResult.quality_run_id == quality_run_id)
            .order_by(ShadowClassificationResult.strategy_profile_key.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def load_for_signal(self, signal_id: UUID) -> IntelligenceQualityArtifacts:
        signal = await self.session.get(Signal, signal_id)
        analysis_run = (
            await self.session.get(AnalysisRun, signal.analysis_run_id)
            if signal is not None
            else None
        )
        artifacts = await self.load_for_analysis_run(
            signal.analysis_run_id if signal is not None else UUID(int=0)
        )
        artifacts.signal = signal
        artifacts.analysis_run = analysis_run
        if signal is not None:
            artifacts.confidence_components = await self.list_confidence_components(signal.id)
            artifacts.evidence = await self.list_evidence(signal.id)
            artifacts.risk_notes = await self.list_risk_notes(signal.id)
            artifacts.deterministic_explanation = await self.get_deterministic_explanation(
                signal.id
            )
            artifacts.news_correlations = await self.list_news_correlations(signal.id)
            artifacts.llm_explanation = await self.get_llm_explanation(signal.id)
            artifacts.reasoning_runs = await self.list_reasoning_runs(signal.id, None)
            artifacts.scenario_hypotheses = await self.list_scenarios(artifacts.reasoning_runs)
            artifacts.outcomes = await self.list_signal_outcomes(signal.id)
        return artifacts

    async def load_for_analysis_run(
        self,
        analysis_run_id: UUID,
    ) -> IntelligenceQualityArtifacts:
        analysis_run = await self.session.get(AnalysisRun, analysis_run_id)
        signal = await self.get_signal_by_analysis_run_id(analysis_run_id)
        artifacts = IntelligenceQualityArtifacts(
            analysis_run=analysis_run,
            signal=signal,
            feature_snapshot=await self.get_feature_snapshot(analysis_run_id),
            indicator_snapshot=await self.get_indicator_snapshot(analysis_run_id),
            pattern_candidates=await self.list_pattern_candidates(analysis_run_id),
            deterministic_explanation=await self.get_deterministic_explanation_by_analysis_run(
                analysis_run_id
            ),
            news_correlations=await self.list_news_correlations_by_analysis_run(
                analysis_run_id
            ),
            reasoning_runs=await self.list_reasoning_runs(None, analysis_run_id),
            outcomes=await self.list_analysis_outcomes(analysis_run_id),
            chart_screenshot_runs=await self.list_chart_screenshot_runs(analysis_run_id),
        )
        if signal is not None:
            artifacts.confidence_components = await self.list_confidence_components(signal.id)
            artifacts.evidence = await self.list_evidence(signal.id)
            artifacts.risk_notes = await self.list_risk_notes(signal.id)
            artifacts.deterministic_explanation = (
                await self.get_deterministic_explanation(signal.id)
                or artifacts.deterministic_explanation
            )
            artifacts.news_correlations = await self.list_news_correlations(signal.id)
            artifacts.llm_explanation = await self.get_llm_explanation(signal.id)
            artifacts.reasoning_runs = await self.list_reasoning_runs(signal.id, None)
            artifacts.outcomes = await self.list_signal_outcomes(signal.id)
        artifacts.scenario_hypotheses = await self.list_scenarios(artifacts.reasoning_runs)
        return artifacts

    async def get_signal_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.analysis_run_id == analysis_run_id)
            .order_by(Signal.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_feature_snapshot(self, analysis_run_id: UUID) -> FeatureSnapshot | None:
        statement: Select[tuple[FeatureSnapshot]] = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(FeatureSnapshot.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_indicator_snapshot(self, analysis_run_id: UUID) -> IndicatorSnapshot | None:
        statement: Select[tuple[IndicatorSnapshot]] = (
            select(IndicatorSnapshot)
            .where(IndicatorSnapshot.analysis_run_id == analysis_run_id)
            .order_by(IndicatorSnapshot.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_pattern_candidates(self, analysis_run_id: UUID) -> list[PatternCandidate]:
        statement: Select[tuple[PatternCandidate]] = (
            select(PatternCandidate)
            .where(PatternCandidate.analysis_run_id == analysis_run_id)
            .order_by(PatternCandidate.is_selected.desc(), PatternCandidate.strength_score.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_confidence_components(
        self,
        signal_id: UUID,
    ) -> list[SignalConfidenceComponent]:
        statement: Select[tuple[SignalConfidenceComponent]] = (
            select(SignalConfidenceComponent)
            .where(SignalConfidenceComponent.signal_id == signal_id)
            .order_by(SignalConfidenceComponent.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

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

    async def get_deterministic_explanation_by_analysis_run(
        self,
        analysis_run_id: UUID,
    ) -> DeterministicExplanation | None:
        statement: Select[tuple[DeterministicExplanation]] = (
            select(DeterministicExplanation)
            .where(DeterministicExplanation.analysis_run_id == analysis_run_id)
            .order_by(DeterministicExplanation.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_llm_explanation(self, signal_id: UUID) -> LlmExplanation | None:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(LlmExplanation.signal_id == signal_id)
            .order_by(LlmExplanation.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_news_correlations(self, signal_id: UUID) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.signal_id == signal_id)
            .order_by(SignalNewsCorrelation.correlation_score.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_news_correlations_by_analysis_run(
        self,
        analysis_run_id: UUID,
    ) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.analysis_run_id == analysis_run_id)
            .order_by(SignalNewsCorrelation.correlation_score.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_reasoning_runs(
        self,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> list[LlmReasoningRun]:
        statement: Select[tuple[LlmReasoningRun]] = select(LlmReasoningRun).order_by(
            LlmReasoningRun.created_at.desc()
        )
        if signal_id is not None:
            statement = statement.where(LlmReasoningRun.signal_id == signal_id)
        if analysis_run_id is not None:
            statement = statement.where(LlmReasoningRun.analysis_run_id == analysis_run_id)
        result = await self.session.execute(statement.limit(25))
        return list(result.scalars().all())

    async def list_scenarios(
        self,
        reasoning_runs: list[LlmReasoningRun],
    ) -> list[ScenarioHypothesis]:
        reasoning_run_ids = [run.id for run in reasoning_runs]
        if not reasoning_run_ids:
            return []
        statement: Select[tuple[ScenarioHypothesis]] = (
            select(ScenarioHypothesis)
            .where(ScenarioHypothesis.reasoning_run_id.in_(reasoning_run_ids))
            .order_by(ScenarioHypothesis.sort_order.asc(), ScenarioHypothesis.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_signal_outcomes(self, signal_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.signal_id == signal_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_analysis_outcomes(self, analysis_run_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.analysis_run_id == analysis_run_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_chart_screenshot_runs(
        self,
        analysis_run_id: UUID,
    ) -> list[ChartScreenshotRun]:
        statement: Select[tuple[ChartScreenshotRun]] = (
            select(ChartScreenshotRun)
            .where(ChartScreenshotRun.analysis_run_id == analysis_run_id)
            .order_by(ChartScreenshotRun.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_active_strategy_profiles(self) -> list[StrategyProfile]:
        statement: Select[tuple[StrategyProfile]] = (
            select(StrategyProfile)
            .where(StrategyProfile.is_active.is_(True))
            .order_by(StrategyProfile.key.asc(), StrategyProfile.version.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
