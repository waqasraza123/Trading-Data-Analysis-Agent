from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionItemStatus
from app.modules.analysis.models import AnalysisRun
from app.modules.cohort_drift.models import CohortDriftResult, CohortDriftRun
from app.modules.confidence_calibration.models import (
    ConfidenceCalibrationBin,
    ConfidenceCalibrationRun,
)
from app.modules.cross_asset_context.models import CrossAssetContextResult, CrossAssetContextRun
from app.modules.data_quality.models import DataQualityRun
from app.modules.decision_readiness.models import DecisionReadinessAssessment
from app.modules.historical_cases.models import HistoricalCaseSearch, HistoricalCaseVector
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFinding,
    IntelligenceQualityRun,
    ShadowClassificationResult,
)
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.outcomes.models import SignalOutcome
from app.modules.setup_context.models import SetupContext
from app.modules.signal_priority.models import SignalPriorityScore
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.timeframe_aggregation.models import MultiTimeframeContext


@dataclass(frozen=True)
class SignalPriorityArtifacts:
    signal: Signal
    analysis_run: AnalysisRun | None
    confidence_components: list[SignalConfidenceComponent] = field(default_factory=list)
    evidence: list[SignalEvidence] = field(default_factory=list)
    risk_notes: list[SignalRiskNote] = field(default_factory=list)
    setup_context: SetupContext | None = None
    market_memory: RollingMarketStateSnapshot | None = None
    data_quality_run: DataQualityRun | None = None
    multi_timeframe_context: MultiTimeframeContext | None = None
    cross_asset_context_run: CrossAssetContextRun | None = None
    cross_asset_results: list[CrossAssetContextResult] = field(default_factory=list)
    historical_case_vector: HistoricalCaseVector | None = None
    historical_case_search: HistoricalCaseSearch | None = None
    outcomes: list[SignalOutcome] = field(default_factory=list)
    confidence_calibration_bin: ConfidenceCalibrationBin | None = None
    cohort_drift_results: list[CohortDriftResult] = field(default_factory=list)
    action_items: list[ReasoningActionItem] = field(default_factory=list)
    decision_readiness: DecisionReadinessAssessment | None = None
    intelligence_quality_run: IntelligenceQualityRun | None = None
    intelligence_quality_findings: list[IntelligenceQualityFinding] = field(default_factory=list)
    shadow_classifications: list[ShadowClassificationResult] = field(default_factory=list)


class SignalPriorityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return await self.session.get(AnalysisRun, analysis_run_id)

    async def get_signal_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.analysis_run_id == analysis_run_id)
            .order_by(Signal.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_signal_version(
        self,
        signal_id: UUID,
        priority_version: str,
    ) -> SignalPriorityScore | None:
        statement: Select[tuple[SignalPriorityScore]] = (
            select(SignalPriorityScore)
            .where(
                SignalPriorityScore.signal_id == signal_id,
                SignalPriorityScore.priority_version == priority_version,
            )
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_for_signal(self, signal_id: UUID) -> SignalPriorityScore | None:
        statement: Select[tuple[SignalPriorityScore]] = (
            select(SignalPriorityScore)
            .where(SignalPriorityScore.signal_id == signal_id)
            .order_by(SignalPriorityScore.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        score: SignalPriorityScore,
        existing: SignalPriorityScore | None,
        force_recompute: bool,
    ) -> SignalPriorityScore:
        if existing is not None and not force_recompute:
            return existing
        if existing is None:
            self.session.add(score)
            await self.session.flush()
            await self.session.refresh(score)
            return score
        copy_priority_score_values(score, existing)
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def list_priority_scores(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        priority_label: str | None = None,
        review_bucket: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
    ) -> list[SignalPriorityScore]:
        statement: Select[tuple[SignalPriorityScore]] = (
            select(SignalPriorityScore)
            .where(SignalPriorityScore.workspace_id == workspace_id)
            .order_by(
                SignalPriorityScore.priority_score.desc(),
                SignalPriorityScore.updated_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if priority_label is not None:
            statement = statement.where(SignalPriorityScore.priority_label == priority_label)
        if review_bucket is not None:
            statement = statement.where(SignalPriorityScore.review_bucket == review_bucket)
        if symbol_id is not None:
            statement = statement.where(SignalPriorityScore.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(SignalPriorityScore.timeframe == timeframe)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_recent_signals(self, workspace_id: UUID, limit: int) -> list[Signal]:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.workspace_id == workspace_id)
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def load_artifacts(
        self,
        signal: Signal,
        quality_gate_version: str,
        shadow_version: str,
        market_memory_version: str,
    ) -> SignalPriorityArtifacts:
        analysis_run = await self.get_analysis_run(signal.analysis_run_id)
        cross_asset_run = await self.get_cross_asset_context_run(signal.id, signal.analysis_run_id)
        quality_run = await self.get_intelligence_quality_run(
            signal.id,
            signal.analysis_run_id,
            quality_gate_version,
            shadow_version,
        )
        return SignalPriorityArtifacts(
            signal=signal,
            analysis_run=analysis_run,
            confidence_components=await self.list_confidence_components(signal.id),
            evidence=await self.list_evidence(signal.id),
            risk_notes=await self.list_risk_notes(signal.id),
            setup_context=await self.get_setup_context(signal.id),
            market_memory=await self.get_market_memory(signal, analysis_run, market_memory_version),
            data_quality_run=await self.get_data_quality_run(signal, analysis_run),
            multi_timeframe_context=await self.get_multi_timeframe_context(
                signal.id,
                signal.analysis_run_id,
            ),
            cross_asset_context_run=cross_asset_run,
            cross_asset_results=await self.list_cross_asset_results(cross_asset_run),
            historical_case_vector=await self.get_historical_case_vector(signal.id),
            historical_case_search=await self.get_historical_case_search(signal.id),
            outcomes=await self.list_outcomes(signal.id),
            confidence_calibration_bin=await self.get_confidence_calibration_bin(signal),
            cohort_drift_results=await self.list_cohort_drift_results(signal),
            action_items=await self.list_pending_action_items(signal.id, signal.analysis_run_id),
            decision_readiness=await self.get_decision_readiness(signal.id, signal.analysis_run_id),
            intelligence_quality_run=quality_run,
            intelligence_quality_findings=await self.list_quality_findings(quality_run),
            shadow_classifications=await self.list_shadow_classifications(quality_run),
        )

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

    async def get_setup_context(self, signal_id: UUID) -> SetupContext | None:
        statement: Select[tuple[SetupContext]] = (
            select(SetupContext)
            .where(SetupContext.signal_id == signal_id)
            .order_by(SetupContext.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_market_memory(
        self,
        signal: Signal,
        analysis_run: AnalysisRun | None,
        state_version: str,
    ) -> RollingMarketStateSnapshot | None:
        statement: Select[tuple[RollingMarketStateSnapshot]] = (
            select(RollingMarketStateSnapshot)
            .where(
                RollingMarketStateSnapshot.workspace_id == signal.workspace_id,
                RollingMarketStateSnapshot.symbol_id == signal.symbol_id,
                RollingMarketStateSnapshot.timeframe == signal.timeframe,
                RollingMarketStateSnapshot.state_version == state_version,
                or_(
                    RollingMarketStateSnapshot.latest_signal_id == signal.id,
                    RollingMarketStateSnapshot.latest_analysis_run_id == signal.analysis_run_id,
                ),
            )
            .order_by(RollingMarketStateSnapshot.updated_at.desc())
            .limit(1)
        )
        if analysis_run is not None and analysis_run.source_id is not None:
            statement = statement.where(
                or_(
                    RollingMarketStateSnapshot.source_id == analysis_run.source_id,
                    RollingMarketStateSnapshot.source_id.is_(None),
                )
            )
        result = await self.session.execute(statement)
        snapshot = result.scalar_one_or_none()
        if snapshot is not None:
            return snapshot
        fallback: Select[tuple[RollingMarketStateSnapshot]] = (
            select(RollingMarketStateSnapshot)
            .where(
                RollingMarketStateSnapshot.workspace_id == signal.workspace_id,
                RollingMarketStateSnapshot.symbol_id == signal.symbol_id,
                RollingMarketStateSnapshot.timeframe == signal.timeframe,
                RollingMarketStateSnapshot.state_version == state_version,
            )
            .order_by(RollingMarketStateSnapshot.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(fallback)
        return result.scalar_one_or_none()

    async def get_data_quality_run(
        self,
        signal: Signal,
        analysis_run: AnalysisRun | None,
    ) -> DataQualityRun | None:
        statement: Select[tuple[DataQualityRun]] = (
            select(DataQualityRun)
            .where(
                DataQualityRun.workspace_id == signal.workspace_id,
                DataQualityRun.symbol_id == signal.symbol_id,
                DataQualityRun.timeframe == signal.timeframe,
            )
            .order_by(DataQualityRun.created_at.desc())
            .limit(1)
        )
        if analysis_run is not None and analysis_run.source_id is not None:
            statement = statement.where(DataQualityRun.source_id == analysis_run.source_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_multi_timeframe_context(
        self,
        signal_id: UUID,
        analysis_run_id: UUID,
    ) -> MultiTimeframeContext | None:
        statement: Select[tuple[MultiTimeframeContext]] = (
            select(MultiTimeframeContext)
            .where(
                or_(
                    MultiTimeframeContext.signal_id == signal_id,
                    MultiTimeframeContext.analysis_run_id == analysis_run_id,
                )
            )
            .order_by(MultiTimeframeContext.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_cross_asset_context_run(
        self,
        signal_id: UUID,
        analysis_run_id: UUID,
    ) -> CrossAssetContextRun | None:
        statement: Select[tuple[CrossAssetContextRun]] = (
            select(CrossAssetContextRun)
            .where(
                or_(
                    CrossAssetContextRun.signal_id == signal_id,
                    CrossAssetContextRun.analysis_run_id == analysis_run_id,
                )
            )
            .order_by(CrossAssetContextRun.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_cross_asset_results(
        self,
        run: CrossAssetContextRun | None,
    ) -> list[CrossAssetContextResult]:
        if run is None:
            return []
        statement: Select[tuple[CrossAssetContextResult]] = (
            select(CrossAssetContextResult)
            .where(CrossAssetContextResult.context_run_id == run.id)
            .order_by(CrossAssetContextResult.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_historical_case_vector(self, signal_id: UUID) -> HistoricalCaseVector | None:
        statement: Select[tuple[HistoricalCaseVector]] = (
            select(HistoricalCaseVector)
            .where(HistoricalCaseVector.signal_id == signal_id)
            .order_by(HistoricalCaseVector.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_historical_case_search(self, signal_id: UUID) -> HistoricalCaseSearch | None:
        statement: Select[tuple[HistoricalCaseSearch]] = (
            select(HistoricalCaseSearch)
            .where(HistoricalCaseSearch.source_signal_id == signal_id)
            .order_by(HistoricalCaseSearch.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_outcomes(self, signal_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.signal_id == signal_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_confidence_calibration_bin(
        self,
        signal: Signal,
    ) -> ConfidenceCalibrationBin | None:
        run_statement: Select[tuple[ConfidenceCalibrationRun]] = (
            select(ConfidenceCalibrationRun)
            .where(ConfidenceCalibrationRun.workspace_id == signal.workspace_id)
            .order_by(ConfidenceCalibrationRun.created_at.desc())
            .limit(1)
        )
        run_result = await self.session.execute(run_statement)
        run = run_result.scalar_one_or_none()
        if run is None:
            return None
        statement: Select[tuple[ConfidenceCalibrationBin]] = (
            select(ConfidenceCalibrationBin)
            .where(
                ConfidenceCalibrationBin.calibration_run_id == run.id,
                ConfidenceCalibrationBin.bin_min <= signal.confidence_score,
                ConfidenceCalibrationBin.bin_max >= signal.confidence_score,
            )
            .order_by(
                ConfidenceCalibrationBin.sample_size.desc(),
                ConfidenceCalibrationBin.horizon_minutes.asc(),
            )
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_cohort_drift_results(self, signal: Signal) -> list[CohortDriftResult]:
        statement: Select[tuple[CohortDriftResult]] = (
            select(CohortDriftResult)
            .join(CohortDriftRun, CohortDriftRun.id == CohortDriftResult.drift_run_id)
            .where(CohortDriftResult.workspace_id == signal.workspace_id)
            .order_by(CohortDriftRun.created_at.desc(), CohortDriftResult.drift_score.desc())
            .limit(10)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_pending_action_items(
        self,
        signal_id: UUID,
        analysis_run_id: UUID,
    ) -> list[ReasoningActionItem]:
        statement: Select[tuple[ReasoningActionItem]] = (
            select(ReasoningActionItem)
            .where(
                ReasoningActionItem.status.in_(
                    [
                        ReasoningActionItemStatus.PENDING.value,
                        ReasoningActionItemStatus.DUE.value,
                    ]
                ),
                or_(
                    ReasoningActionItem.signal_id == signal_id,
                    ReasoningActionItem.analysis_run_id == analysis_run_id,
                ),
            )
            .order_by(
                ReasoningActionItem.priority.desc(),
                ReasoningActionItem.due_at.asc().nullsfirst(),
                ReasoningActionItem.created_at.asc(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_decision_readiness(
        self,
        signal_id: UUID,
        analysis_run_id: UUID,
    ) -> DecisionReadinessAssessment | None:
        statement: Select[tuple[DecisionReadinessAssessment]] = (
            select(DecisionReadinessAssessment)
            .where(
                or_(
                    DecisionReadinessAssessment.signal_id == signal_id,
                    DecisionReadinessAssessment.analysis_run_id == analysis_run_id,
                )
            )
            .order_by(DecisionReadinessAssessment.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_intelligence_quality_run(
        self,
        signal_id: UUID,
        analysis_run_id: UUID,
        gate_version: str,
        shadow_version: str,
    ) -> IntelligenceQualityRun | None:
        statement: Select[tuple[IntelligenceQualityRun]] = (
            select(IntelligenceQualityRun)
            .where(
                or_(
                    IntelligenceQualityRun.signal_id == signal_id,
                    IntelligenceQualityRun.analysis_run_id == analysis_run_id,
                ),
                IntelligenceQualityRun.gate_version == gate_version,
                IntelligenceQualityRun.shadow_version == shadow_version,
            )
            .order_by(IntelligenceQualityRun.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_quality_findings(
        self,
        quality_run: IntelligenceQualityRun | None,
    ) -> list[IntelligenceQualityFinding]:
        if quality_run is None:
            return []
        statement: Select[tuple[IntelligenceQualityFinding]] = (
            select(IntelligenceQualityFinding)
            .where(IntelligenceQualityFinding.quality_run_id == quality_run.id)
            .order_by(IntelligenceQualityFinding.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_shadow_classifications(
        self,
        quality_run: IntelligenceQualityRun | None,
    ) -> list[ShadowClassificationResult]:
        if quality_run is None:
            return []
        statement: Select[tuple[ShadowClassificationResult]] = (
            select(ShadowClassificationResult)
            .where(ShadowClassificationResult.quality_run_id == quality_run.id)
            .order_by(ShadowClassificationResult.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())


def copy_priority_score_values(source: SignalPriorityScore, target: SignalPriorityScore) -> None:
    target.workspace_id = source.workspace_id
    target.analysis_run_id = source.analysis_run_id
    target.symbol_id = source.symbol_id
    target.timeframe = source.timeframe
    target.priority_score = source.priority_score
    target.priority_label = source.priority_label
    target.review_bucket = source.review_bucket
    target.component_scores_json = source.component_scores_json
    target.penalties_json = source.penalties_json
    target.boosters_json = source.boosters_json
    target.reasons_json = source.reasons_json
    target.warnings_json = source.warnings_json
