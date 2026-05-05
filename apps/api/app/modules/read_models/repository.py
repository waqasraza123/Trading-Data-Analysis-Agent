from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionItemStatus
from app.modules.analysis.models import AnalysisRun
from app.modules.daily_briefs.models import DailyBriefRun
from app.modules.data_quality.models import DataQualityRun
from app.modules.decision_readiness.models import DecisionReadinessAssessment
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_regimes.models import MarketRegimeContext
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.outcomes.models import SignalOutcome
from app.modules.provider_health.models import ProviderHealthSnapshot
from app.modules.read_models.models import (
    CommandCenterReadModel,
    DashboardSymbolReadModel,
    SignalCardReadModel,
)
from app.modules.read_models.schemas import (
    DashboardSymbolReadModelFilters,
    SignalCardReadModelFilters,
)
from app.modules.setup_context.models import SetupContext
from app.modules.signal_priority.models import SignalPriorityScore
from app.modules.signals.models import Signal, SignalEvidence, SignalRiskNote
from app.modules.symbols.models import Symbol
from app.modules.workspaces.models import Workspace


@dataclass(frozen=True)
class SignalCardArtifacts:
    signal: Signal
    analysis_run: AnalysisRun | None
    market_memory: RollingMarketStateSnapshot | None = None
    priority: SignalPriorityScore | None = None
    setup_context: SetupContext | None = None
    outcomes: list[SignalOutcome] = field(default_factory=list)
    evidence: list[SignalEvidence] = field(default_factory=list)
    risk_notes: list[SignalRiskNote] = field(default_factory=list)
    action_items: list[ReasoningActionItem] = field(default_factory=list)
    data_quality: DataQualityRun | None = None
    provider_health: ProviderHealthSnapshot | None = None
    readiness: DecisionReadinessAssessment | None = None
    market_regime: MarketRegimeContext | None = None
    market_session: MarketSessionContext | None = None


@dataclass(frozen=True)
class SymbolReadModelArtifacts:
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    market_memory: RollingMarketStateSnapshot | None = None
    latest_signal: Signal | None = None
    priority: SignalPriorityScore | None = None
    setup_context: SetupContext | None = None
    action_items: list[ReasoningActionItem] = field(default_factory=list)
    data_quality: DataQualityRun | None = None
    provider_health: ProviderHealthSnapshot | None = None
    market_regime: MarketRegimeContext | None = None
    market_session: MarketSessionContext | None = None


@dataclass(frozen=True)
class CommandCenterArtifacts:
    workspace_id: UUID
    latest_brief: DailyBriefRun | None
    signal_cards: list[SignalCardReadModel]
    symbol_models: list[DashboardSymbolReadModel]


class ReadModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

    async def get_symbol(self, symbol_id: UUID) -> Symbol | None:
        return await self.session.get(Symbol, symbol_id)

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return await self.session.get(AnalysisRun, analysis_run_id)

    async def list_recent_signals(self, workspace_id: UUID, limit: int) -> list[Signal]:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.workspace_id == workspace_id)
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def load_signal_artifacts(
        self,
        signal: Signal,
        market_memory_version: str,
    ) -> SignalCardArtifacts:
        analysis_run = await self.get_analysis_run(signal.analysis_run_id)
        return SignalCardArtifacts(
            signal=signal,
            analysis_run=analysis_run,
            market_memory=await self.get_market_memory(
                workspace_id=signal.workspace_id,
                symbol_id=signal.symbol_id,
                timeframe=signal.timeframe,
                state_version=market_memory_version,
                source_id=analysis_run.source_id if analysis_run is not None else None,
                signal_id=signal.id,
                analysis_run_id=signal.analysis_run_id,
            ),
            priority=await self.get_latest_signal_priority(signal.id),
            setup_context=await self.get_latest_setup_context(signal.id, signal.analysis_run_id),
            outcomes=await self.list_outcomes(signal.id),
            evidence=await self.list_evidence(signal.id),
            risk_notes=await self.list_risk_notes(signal.id),
            action_items=await self.list_pending_action_items(signal.id, signal.analysis_run_id),
            data_quality=await self.get_latest_data_quality(
                workspace_id=signal.workspace_id,
                symbol_id=signal.symbol_id,
                timeframe=signal.timeframe,
                source_id=analysis_run.source_id if analysis_run is not None else None,
            ),
            provider_health=await self.get_latest_provider_health(
                workspace_id=signal.workspace_id,
                symbol_id=signal.symbol_id,
                timeframe=signal.timeframe,
                source_id=analysis_run.source_id if analysis_run is not None else None,
            ),
            readiness=await self.get_latest_readiness(signal.id, signal.analysis_run_id),
            market_regime=await self.get_latest_market_regime(signal.id, signal.analysis_run_id),
            market_session=await self.get_latest_market_session(signal.id, signal.analysis_run_id),
        )

    async def load_symbol_artifacts(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None,
        market_memory_version: str,
    ) -> SymbolReadModelArtifacts:
        market_memory = await self.get_market_memory(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            state_version=market_memory_version,
            source_id=source_id,
            signal_id=None,
            analysis_run_id=None,
        )
        latest_signal = await self.get_latest_signal(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            signal_id=market_memory.latest_signal_id if market_memory is not None else None,
        )
        return SymbolReadModelArtifacts(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe,
            market_memory=market_memory,
            latest_signal=latest_signal,
            priority=await self.get_latest_signal_priority(latest_signal.id)
            if latest_signal is not None
            else None,
            setup_context=await self.get_latest_setup_context(
                latest_signal.id,
                latest_signal.analysis_run_id,
            )
            if latest_signal is not None
            else None,
            action_items=await self.list_pending_action_items(
                latest_signal.id,
                latest_signal.analysis_run_id,
            )
            if latest_signal is not None
            else [],
            data_quality=await self.get_latest_data_quality(
                workspace_id=workspace_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                source_id=source_id,
            ),
            provider_health=await self.get_latest_provider_health(
                workspace_id=workspace_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                source_id=source_id,
            ),
            market_regime=await self.get_latest_market_regime(
                latest_signal.id if latest_signal is not None else None,
                latest_signal.analysis_run_id if latest_signal is not None else None,
            ),
            market_session=await self.get_latest_market_session(
                latest_signal.id if latest_signal is not None else None,
                latest_signal.analysis_run_id if latest_signal is not None else None,
            ),
        )

    async def load_command_center_artifacts(
        self,
        workspace_id: UUID,
        read_model_version: str,
        limit: int,
    ) -> CommandCenterArtifacts:
        return CommandCenterArtifacts(
            workspace_id=workspace_id,
            latest_brief=await self.get_latest_daily_brief(workspace_id),
            signal_cards=await self.list_recent_signal_cards(
                workspace_id, read_model_version, limit
            ),
            symbol_models=await self.list_recent_symbol_models(
                workspace_id, read_model_version, limit
            ),
        )

    async def get_market_memory(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        state_version: str,
        source_id: UUID | None,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> RollingMarketStateSnapshot | None:
        statement: Select[tuple[RollingMarketStateSnapshot]] = (
            select(RollingMarketStateSnapshot)
            .where(
                RollingMarketStateSnapshot.workspace_id == workspace_id,
                RollingMarketStateSnapshot.symbol_id == symbol_id,
                RollingMarketStateSnapshot.timeframe == timeframe,
                RollingMarketStateSnapshot.state_version == state_version,
            )
            .order_by(RollingMarketStateSnapshot.updated_at.desc())
            .limit(1)
        )
        if source_id is not None:
            statement = statement.where(
                or_(
                    RollingMarketStateSnapshot.source_id == source_id,
                    RollingMarketStateSnapshot.source_id.is_(None),
                )
            )
        if signal_id is not None or analysis_run_id is not None:
            identity_filters = []
            if signal_id is not None:
                identity_filters.append(RollingMarketStateSnapshot.latest_signal_id == signal_id)
            if analysis_run_id is not None:
                identity_filters.append(
                    RollingMarketStateSnapshot.latest_analysis_run_id == analysis_run_id
                )
            focused = statement.where(or_(*identity_filters))
            result = await self.session.execute(focused)
            snapshot = result.scalar_one_or_none()
            if snapshot is not None:
                return snapshot
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_signal(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        signal_id: UUID | None,
    ) -> Signal | None:
        if signal_id is not None:
            signal = await self.get_signal(signal_id)
            if signal is not None:
                return signal
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(
                Signal.workspace_id == workspace_id,
                Signal.symbol_id == symbol_id,
                Signal.timeframe == timeframe,
            )
            .order_by(Signal.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_signal_priority(self, signal_id: UUID) -> SignalPriorityScore | None:
        statement: Select[tuple[SignalPriorityScore]] = (
            select(SignalPriorityScore)
            .where(SignalPriorityScore.signal_id == signal_id)
            .order_by(SignalPriorityScore.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_setup_context(
        self,
        signal_id: UUID,
        analysis_run_id: UUID,
    ) -> SetupContext | None:
        statement: Select[tuple[SetupContext]] = (
            select(SetupContext)
            .where(
                or_(
                    SetupContext.signal_id == signal_id,
                    SetupContext.analysis_run_id == analysis_run_id,
                )
            )
            .order_by(SetupContext.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_outcomes(self, signal_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.signal_id == signal_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.updated_at.desc())
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

    async def get_latest_data_quality(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None,
    ) -> DataQualityRun | None:
        statement: Select[tuple[DataQualityRun]] = (
            select(DataQualityRun)
            .where(
                DataQualityRun.workspace_id == workspace_id,
                DataQualityRun.symbol_id == symbol_id,
                DataQualityRun.timeframe == timeframe,
            )
            .order_by(DataQualityRun.created_at.desc())
            .limit(1)
        )
        if source_id is not None:
            statement = statement.where(DataQualityRun.source_id == source_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_provider_health(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None,
    ) -> ProviderHealthSnapshot | None:
        statement: Select[tuple[ProviderHealthSnapshot]] = (
            select(ProviderHealthSnapshot)
            .where(
                ProviderHealthSnapshot.workspace_id == workspace_id,
                ProviderHealthSnapshot.symbol_id == symbol_id,
                ProviderHealthSnapshot.timeframe == timeframe,
            )
            .order_by(ProviderHealthSnapshot.created_at.desc())
            .limit(1)
        )
        if source_id is not None:
            statement = statement.where(ProviderHealthSnapshot.source_id == source_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_readiness(
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

    async def get_latest_market_regime(
        self,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> MarketRegimeContext | None:
        if signal_id is None and analysis_run_id is None:
            return None
        statement: Select[tuple[MarketRegimeContext]] = select(MarketRegimeContext).order_by(
            MarketRegimeContext.updated_at.desc()
        )
        if signal_id is not None:
            statement = statement.where(MarketRegimeContext.signal_id == signal_id)
        elif analysis_run_id is not None:
            statement = statement.where(MarketRegimeContext.analysis_run_id == analysis_run_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_market_session(
        self,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> MarketSessionContext | None:
        if signal_id is None and analysis_run_id is None:
            return None
        statement: Select[tuple[MarketSessionContext]] = select(MarketSessionContext).order_by(
            MarketSessionContext.updated_at.desc()
        )
        if signal_id is not None:
            statement = statement.where(MarketSessionContext.signal_id == signal_id)
        elif analysis_run_id is not None:
            statement = statement.where(MarketSessionContext.analysis_run_id == analysis_run_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_daily_brief(self, workspace_id: UUID) -> DailyBriefRun | None:
        statement: Select[tuple[DailyBriefRun]] = (
            select(DailyBriefRun)
            .where(DailyBriefRun.workspace_id == workspace_id)
            .order_by(DailyBriefRun.generated_at.desc(), DailyBriefRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_symbol_read_model(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
        timeframe: str,
        read_model_version: str,
    ) -> DashboardSymbolReadModel | None:
        statement: Select[tuple[DashboardSymbolReadModel]] = select(DashboardSymbolReadModel).where(
            DashboardSymbolReadModel.workspace_id == workspace_id,
            DashboardSymbolReadModel.symbol_id == symbol_id,
            DashboardSymbolReadModel.timeframe == timeframe,
            DashboardSymbolReadModel.read_model_version == read_model_version,
        )
        if source_id is None:
            statement = statement.where(DashboardSymbolReadModel.source_id.is_(None))
        else:
            statement = statement.where(DashboardSymbolReadModel.source_id == source_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_signal_card(
        self,
        signal_id: UUID,
        read_model_version: str,
    ) -> SignalCardReadModel | None:
        statement: Select[tuple[SignalCardReadModel]] = select(SignalCardReadModel).where(
            SignalCardReadModel.signal_id == signal_id,
            SignalCardReadModel.read_model_version == read_model_version,
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def upsert_symbol_model(
        self,
        model: DashboardSymbolReadModel,
        existing: DashboardSymbolReadModel | None,
    ) -> DashboardSymbolReadModel:
        if existing is None:
            self.session.add(model)
            await self.session.flush()
            await self.session.refresh(model)
            return model
        copy_symbol_model(model, existing)
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def upsert_signal_card(
        self,
        model: SignalCardReadModel,
        existing: SignalCardReadModel | None,
    ) -> SignalCardReadModel:
        if existing is None:
            self.session.add(model)
            await self.session.flush()
            await self.session.refresh(model)
            return model
        copy_signal_card(model, existing)
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def create_command_center_model(
        self,
        model: CommandCenterReadModel,
    ) -> CommandCenterReadModel:
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def list_symbol_read_models(
        self,
        filters: DashboardSymbolReadModelFilters,
        read_model_version: str,
    ) -> list[DashboardSymbolReadModel]:
        statement: Select[tuple[DashboardSymbolReadModel]] = (
            select(DashboardSymbolReadModel)
            .where(
                DashboardSymbolReadModel.workspace_id == filters.workspace_id,
                DashboardSymbolReadModel.read_model_version == read_model_version,
            )
            .order_by(
                DashboardSymbolReadModel.updated_at.desc(),
                DashboardSymbolReadModel.created_at.desc(),
            )
            .limit(filters.limit)
            .offset(filters.offset)
        )
        if filters.symbol_id is not None:
            statement = statement.where(DashboardSymbolReadModel.symbol_id == filters.symbol_id)
        if filters.source_id is not None:
            statement = statement.where(DashboardSymbolReadModel.source_id == filters.source_id)
        if filters.timeframe is not None:
            statement = statement.where(DashboardSymbolReadModel.timeframe == filters.timeframe)
        if filters.freshness_label is not None:
            statement = statement.where(
                DashboardSymbolReadModel.freshness_label == filters.freshness_label
            )
        if filters.data_quality_label is not None:
            statement = statement.where(
                DashboardSymbolReadModel.data_quality_label == filters.data_quality_label
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_signal_cards(
        self,
        filters: SignalCardReadModelFilters,
        read_model_version: str,
    ) -> list[SignalCardReadModel]:
        statement: Select[tuple[SignalCardReadModel]] = (
            select(SignalCardReadModel)
            .where(
                SignalCardReadModel.workspace_id == filters.workspace_id,
                SignalCardReadModel.read_model_version == read_model_version,
            )
            .order_by(
                SignalCardReadModel.priority_score.desc().nullslast(),
                SignalCardReadModel.updated_at.desc(),
            )
            .limit(filters.limit)
            .offset(filters.offset)
        )
        if filters.symbol_id is not None:
            statement = statement.where(SignalCardReadModel.symbol_id == filters.symbol_id)
        if filters.timeframe is not None:
            statement = statement.where(SignalCardReadModel.timeframe == filters.timeframe)
        if filters.classification_status is not None:
            statement = statement.where(
                SignalCardReadModel.classification_status == filters.classification_status
            )
        if filters.bias is not None:
            statement = statement.where(SignalCardReadModel.bias == filters.bias)
        if filters.review_bucket is not None:
            statement = statement.where(SignalCardReadModel.review_bucket == filters.review_bucket)
        if filters.priority_label is not None:
            statement = statement.where(
                SignalCardReadModel.priority_label == filters.priority_label
            )
        if filters.freshness_label is not None:
            statement = statement.where(
                SignalCardReadModel.freshness_label == filters.freshness_label
            )
        if filters.data_quality_label is not None:
            statement = statement.where(
                SignalCardReadModel.data_quality_label == filters.data_quality_label
            )
        if filters.readiness_label is not None:
            statement = statement.where(
                SignalCardReadModel.readiness_label == filters.readiness_label
            )
        if filters.search is not None:
            statement = statement.where(
                SignalCardReadModel.searchable_text.ilike(f"%{filters.search}%")
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_command_center_model(
        self,
        workspace_id: UUID,
        read_model_version: str,
    ) -> CommandCenterReadModel | None:
        statement: Select[tuple[CommandCenterReadModel]] = (
            select(CommandCenterReadModel)
            .where(
                CommandCenterReadModel.workspace_id == workspace_id,
                CommandCenterReadModel.read_model_version == read_model_version,
            )
            .order_by(
                CommandCenterReadModel.generated_at.desc(), CommandCenterReadModel.created_at.desc()
            )
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_recent_signal_cards(
        self,
        workspace_id: UUID,
        read_model_version: str,
        limit: int,
    ) -> list[SignalCardReadModel]:
        filters = SignalCardReadModelFilters(workspace_id=workspace_id, limit=limit, offset=0)
        return await self.list_signal_cards(filters, read_model_version)

    async def list_recent_symbol_models(
        self,
        workspace_id: UUID,
        read_model_version: str,
        limit: int,
    ) -> list[DashboardSymbolReadModel]:
        filters = DashboardSymbolReadModelFilters(workspace_id=workspace_id, limit=limit, offset=0)
        return await self.list_symbol_read_models(filters, read_model_version)


def copy_symbol_model(source: DashboardSymbolReadModel, target: DashboardSymbolReadModel) -> None:
    target.latest_final_candle_time = source.latest_final_candle_time
    target.freshness_label = source.freshness_label
    target.data_quality_label = source.data_quality_label
    target.latest_signal_id = source.latest_signal_id
    target.latest_bias = source.latest_bias
    target.latest_pattern_type = source.latest_pattern_type
    target.latest_confidence_label = source.latest_confidence_label
    target.latest_priority_score = source.latest_priority_score
    target.latest_priority_label = source.latest_priority_label
    target.setup_quality_label = source.setup_quality_label
    target.market_regime_label = source.market_regime_label
    target.market_session_label = source.market_session_label
    target.pending_action_count = source.pending_action_count
    target.warning_count = source.warning_count
    target.summary_json = source.summary_json


def copy_signal_card(source: SignalCardReadModel, target: SignalCardReadModel) -> None:
    target.workspace_id = source.workspace_id
    target.analysis_run_id = source.analysis_run_id
    target.symbol_id = source.symbol_id
    target.timeframe = source.timeframe
    target.classification_status = source.classification_status
    target.bias = source.bias
    target.pattern_type = source.pattern_type
    target.confidence_score = source.confidence_score
    target.confidence_label = source.confidence_label
    target.priority_score = source.priority_score
    target.priority_label = source.priority_label
    target.review_bucket = source.review_bucket
    target.setup_quality_label = source.setup_quality_label
    target.freshness_label = source.freshness_label
    target.data_quality_label = source.data_quality_label
    target.readiness_label = source.readiness_label
    target.outcome_summary_json = source.outcome_summary_json
    target.evidence_summary_json = source.evidence_summary_json
    target.risk_summary_json = source.risk_summary_json
    target.action_summary_json = source.action_summary_json
    target.warning_summary_json = source.warning_summary_json
    target.searchable_text = source.searchable_text
