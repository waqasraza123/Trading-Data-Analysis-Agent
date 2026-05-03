from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.outcomes.models import SignalOutcome
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendation,
    PatternOutcomeDiagnostic,
    StrategyProfileDiagnostic,
)
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.symbols.models import Symbol
from app.modules.webhook_outbox.models import (
    WebhookEventType,
    WebhookOutboxEvent,
    WebhookOutboxEventStatus,
    WebhookSubscription,
    WebhookSubscriptionStatus,
)


class WebhookOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_subscription(
        self,
        subscription: WebhookSubscription,
    ) -> WebhookSubscription:
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def get_subscription(self, subscription_id: UUID) -> WebhookSubscription | None:
        return await self.session.get(WebhookSubscription, subscription_id)

    async def list_subscriptions(
        self,
        workspace_id: UUID,
        status: WebhookSubscriptionStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookSubscription]:
        statement: Select[tuple[WebhookSubscription]] = (
            select(WebhookSubscription)
            .where(WebhookSubscription.workspace_id == workspace_id)
            .order_by(WebhookSubscription.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(WebhookSubscription.status == status.value)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_subscription(
        self,
        subscription: WebhookSubscription,
    ) -> WebhookSubscription:
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def create_outbox_event(self, event: WebhookOutboxEvent) -> WebhookOutboxEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get_outbox_event(self, event_id: UUID) -> WebhookOutboxEvent | None:
        return await self.session.get(WebhookOutboxEvent, event_id)

    async def list_outbox_events(
        self,
        workspace_id: UUID,
        event_type: WebhookEventType | None = None,
        status: WebhookOutboxEventStatus | None = None,
        source_type: str | None = None,
        source_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookOutboxEvent]:
        statement: Select[tuple[WebhookOutboxEvent]] = (
            select(WebhookOutboxEvent)
            .where(WebhookOutboxEvent.workspace_id == workspace_id)
            .order_by(WebhookOutboxEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if event_type is not None:
            statement = statement.where(WebhookOutboxEvent.event_type == event_type.value)
        if status is not None:
            statement = statement.where(WebhookOutboxEvent.status == status.value)
        if source_type is not None:
            statement = statement.where(WebhookOutboxEvent.source_type == source_type)
        if source_id is not None:
            statement = statement.where(WebhookOutboxEvent.source_id == source_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_outbox_event(self, event: WebhookOutboxEvent) -> WebhookOutboxEvent:
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_symbol(self, symbol_id: UUID) -> Symbol | None:
        return await self.session.get(Symbol, symbol_id)

    async def list_signal_evidence(self, signal_id: UUID) -> list[SignalEvidence]:
        result = await self.session.execute(
            select(SignalEvidence)
            .where(SignalEvidence.signal_id == signal_id)
            .order_by(SignalEvidence.created_at)
        )
        return list(result.scalars().all())

    async def list_signal_confidence_components(
        self,
        signal_id: UUID,
    ) -> list[SignalConfidenceComponent]:
        result = await self.session.execute(
            select(SignalConfidenceComponent)
            .where(SignalConfidenceComponent.signal_id == signal_id)
            .order_by(SignalConfidenceComponent.created_at)
        )
        return list(result.scalars().all())

    async def list_signal_risk_notes(self, signal_id: UUID) -> list[SignalRiskNote]:
        result = await self.session.execute(
            select(SignalRiskNote)
            .where(SignalRiskNote.signal_id == signal_id)
            .order_by(SignalRiskNote.created_at)
        )
        return list(result.scalars().all())

    async def get_outcome(self, outcome_id: UUID) -> SignalOutcome | None:
        return await self.session.get(SignalOutcome, outcome_id)

    async def get_reasoning_run(self, reasoning_run_id: UUID) -> LlmReasoningRun | None:
        return await self.session.get(LlmReasoningRun, reasoning_run_id)

    async def list_scenarios(self, reasoning_run_id: UUID) -> list[ScenarioHypothesis]:
        result = await self.session.execute(
            select(ScenarioHypothesis)
            .where(ScenarioHypothesis.reasoning_run_id == reasoning_run_id)
            .order_by(ScenarioHypothesis.sort_order.asc(), ScenarioHypothesis.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_action_plan(self, action_plan_id: UUID) -> ReasoningActionPlan | None:
        return await self.session.get(ReasoningActionPlan, action_plan_id)

    async def list_action_items(self, action_plan_id: UUID) -> list[ReasoningActionItem]:
        result = await self.session.execute(
            select(ReasoningActionItem)
            .where(ReasoningActionItem.action_plan_id == action_plan_id)
            .order_by(ReasoningActionItem.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_action_item(self, action_item_id: UUID) -> ReasoningActionItem | None:
        return await self.session.get(ReasoningActionItem, action_item_id)

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return await self.session.get(AnalysisRun, analysis_run_id)

    async def get_chart_screenshot_run(
        self,
        chart_screenshot_run_id: UUID,
    ) -> ChartScreenshotRun | None:
        return await self.session.get(ChartScreenshotRun, chart_screenshot_run_id)

    async def get_strategy_profile_diagnostic(
        self,
        diagnostic_id: UUID,
    ) -> StrategyProfileDiagnostic | None:
        return await self.session.get(StrategyProfileDiagnostic, diagnostic_id)

    async def get_pattern_outcome_diagnostic(
        self,
        diagnostic_id: UUID,
    ) -> PatternOutcomeDiagnostic | None:
        return await self.session.get(PatternOutcomeDiagnostic, diagnostic_id)

    async def get_calibration_recommendation(
        self,
        recommendation_id: UUID,
    ) -> CalibrationRecommendation | None:
        return await self.session.get(CalibrationRecommendation, recommendation_id)
