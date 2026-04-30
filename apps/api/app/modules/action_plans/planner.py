from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.action_plans.models import (
    ActionPlanCreatedFrom,
    ActionPlanSourceType,
    ActionPlanStatus,
    ReasoningActionItem,
    ReasoningActionItemStatus,
    ReasoningActionPlan,
    ReasoningActionPriority,
    ReasoningActionType,
)
from app.modules.action_plans.repository import ReasoningActionPlanRepository
from app.modules.action_plans.validation import validate_backend_actions
from app.modules.analysis.models import AnalysisAuditLog, AnalysisMode, AnalysisRun
from app.modules.analysis.repository import AnalysisRepository
from app.modules.candles.service import CandleService
from app.modules.candles.timeframes import Timeframe, timeframe_duration
from app.modules.news.repository import NewsCorrelationRepository
from app.modules.outcomes.repository import OutcomeRepository
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.reasoning.repository import ScenarioReasoningRepository
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository

ACTION_PLAN_VERSION = "reasoning_action_plan_v1"
MAX_ACTION_ITEMS_PER_PLAN = 24


@dataclass
class ActionPlanBuildResult:
    plan: ReasoningActionPlan
    items: list[ReasoningActionItem]
    rejected_actions: list[dict[str, object]] = field(default_factory=list)
    skipped_actions: list[dict[str, object]] = field(default_factory=list)


class ReasoningActionPlanner:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.action_repository = ReasoningActionPlanRepository(session)
        self.reasoning_repository = ScenarioReasoningRepository(session)
        self.signal_repository = SignalRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.outcome_repository = OutcomeRepository(session)
        self.news_correlation_repository = NewsCorrelationRepository(session)
        self.candle_service = CandleService(session)

    async def build_plan_from_reasoning_run(
        self,
        reasoning_run_id: UUID,
        force_recompute: bool = False,
    ) -> ActionPlanBuildResult:
        existing = await self.action_repository.get_latest_by_reasoning_run_id(reasoning_run_id)
        if existing is not None and not force_recompute:
            return ActionPlanBuildResult(
                plan=existing,
                items=await self.action_repository.list_items(existing.id),
                rejected_actions=metadata_list(existing.metadata_json, "rejectedActions"),
                skipped_actions=metadata_list(existing.metadata_json, "skippedActions"),
            )
        reasoning_run = await self.load_reasoning_run(reasoning_run_id)
        if reasoning_run.signal_id is None or reasoning_run.analysis_run_id is None:
            raise AppError(
                422,
                "action_plan_requires_signal_reasoning",
                "Action plans currently require signal scenario reasoning",
            )
        signal = await self.load_signal(reasoning_run.signal_id)
        analysis_run = await self.load_analysis_run(reasoning_run.analysis_run_id)
        scenarios = await self.reasoning_repository.list_scenarios(reasoning_run.id)
        await self.add_audit_log(
            analysis_run.id,
            "reasoning_action_plan_requested",
            "Reasoning action plan requested",
            {"reasoningRunId": str(reasoning_run.id), "forceRecompute": force_recompute},
        )
        requested_actions = collect_requested_actions(scenarios)
        validation = validate_backend_actions(requested_actions)
        rejected_actions = validation.rejected
        skipped_actions: list[dict[str, object]] = []
        accepted_actions = validation.accepted
        if rejected_actions and ReasoningActionType.REQUEST_HUMAN_REVIEW not in accepted_actions:
            accepted_actions.append(ReasoningActionType.REQUEST_HUMAN_REVIEW)
        plan = await self.create_plan(
            reasoning_run=reasoning_run,
            signal=signal,
            analysis_run=analysis_run,
            rejected_actions=rejected_actions,
            skipped_actions=skipped_actions,
            accepted_actions=accepted_actions,
        )
        items: list[ReasoningActionItem] = []
        for action_type in accepted_actions:
            new_items = await self.items_for_action(
                plan=plan,
                reasoning_run=reasoning_run,
                signal=signal,
                analysis_run=analysis_run,
                action_type=action_type,
                skipped_actions=skipped_actions,
            )
            items.extend(new_items)
            if len(items) >= MAX_ACTION_ITEMS_PER_PLAN:
                skipped_actions.append(
                    {"actionType": "plan_limit", "reason": "max_action_items_reached"}
                )
                break
        persisted_items: list[ReasoningActionItem] = []
        for item in items[:MAX_ACTION_ITEMS_PER_PLAN]:
            existing_item = await self.action_repository.get_item_by_idempotency_key(
                item.workspace_id,
                item.idempotency_key,
            )
            if existing_item is not None:
                skipped_actions.append(
                    {
                        "actionType": item.action_type,
                        "reason": "duplicate_idempotency_key",
                        "idempotencyKey": item.idempotency_key,
                    }
                )
                continue
            persisted = await self.action_repository.create_item(item)
            persisted_items.append(persisted)
            await self.add_audit_log(
                analysis_run.id,
                "reasoning_action_item_created",
                "Reasoning action item created",
                {"actionItemId": str(persisted.id), "actionType": persisted.action_type},
            )
        plan.metadata_json = {
            **plan.metadata_json,
            "rejectedActions": rejected_actions,
            "skippedActions": skipped_actions,
            "createdItemCount": len(persisted_items),
        }
        if persisted_items:
            plan.status = ActionPlanStatus.ACTIVE.value
        elif rejected_actions:
            plan.status = ActionPlanStatus.COMPLETED_WITH_WARNINGS.value
        else:
            plan.status = ActionPlanStatus.COMPLETED.value
        await self.action_repository.update_plan(plan)
        await self.add_audit_log(
            analysis_run.id,
            "reasoning_action_plan_created",
            "Reasoning action plan created",
            {
                "actionPlanId": str(plan.id),
                "createdItemCount": len(persisted_items),
                "rejectedActionCount": len(rejected_actions),
                "skippedActionCount": len(skipped_actions),
            },
        )
        for rejected in rejected_actions:
            await self.add_audit_log(
                analysis_run.id,
                "reasoning_action_item_rejected",
                "Reasoning action item rejected",
                rejected,
            )
        return ActionPlanBuildResult(
            plan=plan,
            items=persisted_items,
            rejected_actions=rejected_actions,
            skipped_actions=skipped_actions,
        )

    async def items_for_action(
        self,
        plan: ReasoningActionPlan,
        reasoning_run: LlmReasoningRun,
        signal: Signal,
        analysis_run: AnalysisRun,
        action_type: ReasoningActionType,
        skipped_actions: list[dict[str, object]],
    ) -> list[ReasoningActionItem]:
        if action_type == ReasoningActionType.EVALUATE_OUTCOME_AFTER_HORIZON:
            return await self.outcome_items(
                plan,
                reasoning_run,
                signal,
                analysis_run,
                skipped_actions,
            )
        if action_type == ReasoningActionType.RUN_REPLAY:
            return await self.replay_items(
                plan,
                reasoning_run,
                signal,
                analysis_run,
                skipped_actions,
            )
        if action_type == ReasoningActionType.RUN_NEWS_CORRELATION:
            return await self.news_items(
                plan,
                reasoning_run,
                signal,
                analysis_run,
                skipped_actions,
            )
        if action_type == ReasoningActionType.WAIT_FOR_MORE_FINAL_CANDLES:
            return await self.wait_items(plan, reasoning_run, signal, analysis_run)
        if action_type == ReasoningActionType.REQUEST_HUMAN_REVIEW:
            return [self.base_item(plan, reasoning_run, signal, analysis_run, action_type)]
        if action_type == ReasoningActionType.NO_ACTION:
            skipped_actions.append({"actionType": action_type.value, "reason": "no_action"})
            return []
        raise AppError(422, "unsupported_action_type", "Unsupported action type")

    async def outcome_items(
        self,
        plan: ReasoningActionPlan,
        reasoning_run: LlmReasoningRun,
        signal: Signal,
        analysis_run: AnalysisRun,
        skipped_actions: list[dict[str, object]],
    ) -> list[ReasoningActionItem]:
        items: list[ReasoningActionItem] = []
        for horizon in self.settings.outcome_default_horizons_minutes:
            existing = await self.outcome_repository.get_outcome(
                signal_id=signal.id,
                horizon_minutes=horizon,
                evaluation_version=self.settings.outcome_evaluation_version,
            )
            if existing is not None:
                skipped_actions.append(
                    {
                        "actionType": ReasoningActionType.EVALUATE_OUTCOME_AFTER_HORIZON.value,
                        "reason": "outcome_exists",
                        "horizonMinutes": horizon,
                        "outcomeId": str(existing.id),
                    }
                )
                continue
            due_at = analysis_run.end_time + timedelta(minutes=horizon)
            status = ReasoningActionItemStatus.PENDING.value
            if due_at <= utc_now() and await self.enough_future_candles(analysis_run, horizon):
                status = ReasoningActionItemStatus.DUE.value
            items.append(
                self.base_item(
                    plan,
                    reasoning_run,
                    signal,
                    analysis_run,
                    ReasoningActionType.EVALUATE_OUTCOME_AFTER_HORIZON,
                    status=status,
                    due_at=due_at,
                    horizon_minutes=horizon,
                    input_json={
                        "signalId": str(signal.id),
                        "horizonsMinutes": [horizon],
                        "evaluationVersion": self.settings.outcome_evaluation_version,
                    },
                )
            )
        return items

    async def replay_items(
        self,
        plan: ReasoningActionPlan,
        reasoning_run: LlmReasoningRun,
        signal: Signal,
        analysis_run: AnalysisRun,
        skipped_actions: list[dict[str, object]],
    ) -> list[ReasoningActionItem]:
        if analysis_run.analysis_mode == AnalysisMode.REPLAY.value:
            skipped_actions.append(
                {"actionType": "run_replay", "reason": "replay_of_replay_skipped"}
            )
            return []
        existing_replays = await self.analysis_repository.list_runs(
            limit=1,
            offset=0,
            replayed_from_analysis_run_id=analysis_run.id,
            analysis_mode=AnalysisMode.REPLAY.value,
        )
        if existing_replays:
            skipped_actions.append(
                {
                    "actionType": "run_replay",
                    "reason": "replay_already_exists",
                    "replayAnalysisRunId": str(existing_replays[0].id),
                }
            )
            return []
        return [
            self.base_item(
                plan,
                reasoning_run,
                signal,
                analysis_run,
                ReasoningActionType.RUN_REPLAY,
                due_at=None,
                input_json={
                    "originalAnalysisRunId": str(analysis_run.id),
                    "replayMode": "latest_engine_version",
                    "allowReplayOfReplay": False,
                },
            )
        ]

    async def news_items(
        self,
        plan: ReasoningActionPlan,
        reasoning_run: LlmReasoningRun,
        signal: Signal,
        analysis_run: AnalysisRun,
        skipped_actions: list[dict[str, object]],
    ) -> list[ReasoningActionItem]:
        correlations = await self.news_correlation_repository.list_by_signal_id(signal.id)
        if correlations:
            skipped_actions.append(
                {
                    "actionType": "run_news_correlation",
                    "reason": "news_correlation_exists",
                    "correlationCount": len(correlations),
                }
            )
            return []
        return [
            self.base_item(
                plan,
                reasoning_run,
                signal,
                analysis_run,
                ReasoningActionType.RUN_NEWS_CORRELATION,
                input_json={"signalId": str(signal.id), "analysisRunId": str(analysis_run.id)},
            )
        ]

    async def wait_items(
        self,
        plan: ReasoningActionPlan,
        reasoning_run: LlmReasoningRun,
        signal: Signal,
        analysis_run: AnalysisRun,
    ) -> list[ReasoningActionItem]:
        timeframe = Timeframe(analysis_run.timeframe)
        required_candles = self.settings.outcome_min_future_candles
        due_at = analysis_run.end_time + (timeframe_duration(timeframe) * required_candles)
        status = (
            ReasoningActionItemStatus.DUE.value
            if due_at <= utc_now() and await self.enough_future_candles(analysis_run, None)
            else ReasoningActionItemStatus.PENDING.value
        )
        return [
            self.base_item(
                plan,
                reasoning_run,
                signal,
                analysis_run,
                ReasoningActionType.WAIT_FOR_MORE_FINAL_CANDLES,
                status=status,
                due_at=due_at,
                input_json={
                    "signalId": str(signal.id),
                    "analysisRunId": str(analysis_run.id),
                    "requiredFinalCandleCount": required_candles,
                },
            )
        ]

    def base_item(
        self,
        plan: ReasoningActionPlan,
        reasoning_run: LlmReasoningRun,
        signal: Signal,
        analysis_run: AnalysisRun,
        action_type: ReasoningActionType,
        status: str = ReasoningActionItemStatus.PENDING.value,
        due_at: datetime | None = None,
        horizon_minutes: int | None = None,
        input_json: dict[str, object] | None = None,
    ) -> ReasoningActionItem:
        return ReasoningActionItem(
            id=uuid4(),
            workspace_id=signal.workspace_id,
            action_plan_id=plan.id,
            source_type=ActionPlanSourceType.REASONING_RUN.value,
            source_id=reasoning_run.id,
            signal_id=signal.id,
            analysis_run_id=analysis_run.id,
            reasoning_run_id=reasoning_run.id,
            action_type=action_type.value,
            status=status,
            priority=priority_for_action(action_type).value,
            due_at=due_at,
            horizon_minutes=horizon_minutes,
            idempotency_key=idempotency_key(
                reasoning_run.id,
                signal.id,
                action_type,
                horizon_minutes,
            ),
            input_json=input_json
            or {"signalId": str(signal.id), "analysisRunId": str(analysis_run.id)},
            attempts=0,
            max_attempts=self.settings.reasoning_action_worker_max_attempts,
        )

    async def enough_future_candles(
        self,
        analysis_run: AnalysisRun,
        horizon_minutes: int | None,
    ) -> bool:
        end_time = (
            analysis_run.end_time + timedelta(minutes=horizon_minutes)
            if horizon_minutes is not None
            else utc_now()
        )
        candles = await self.candle_service.fetch_candle_window(
            workspace_id=analysis_run.workspace_id,
            symbol_id=analysis_run.symbol_id,
            timeframe=Timeframe(analysis_run.timeframe),
            start_time=analysis_run.end_time + timedelta(microseconds=1),
            end_time=end_time,
            source_id=analysis_run.source_id,
            include_partial=False,
        )
        return len(candles) >= self.settings.outcome_min_future_candles

    async def create_plan(
        self,
        reasoning_run: LlmReasoningRun,
        signal: Signal,
        analysis_run: AnalysisRun,
        rejected_actions: list[dict[str, object]],
        skipped_actions: list[dict[str, object]],
        accepted_actions: list[ReasoningActionType],
    ) -> ReasoningActionPlan:
        plan = ReasoningActionPlan(
            id=uuid4(),
            workspace_id=reasoning_run.workspace_id,
            source_type=ActionPlanSourceType.REASONING_RUN.value,
            source_id=reasoning_run.id,
            signal_id=signal.id,
            analysis_run_id=analysis_run.id,
            reasoning_run_id=reasoning_run.id,
            status=ActionPlanStatus.PENDING.value,
            plan_version=ACTION_PLAN_VERSION,
            created_from=ActionPlanCreatedFrom.SCENARIO_REASONING.value,
            summary="Backend-safe follow-up plan from grounded scenario reasoning.",
            metadata_json={
                "acceptedActions": [action.value for action in accepted_actions],
                "rejectedActions": rejected_actions,
                "skippedActions": skipped_actions,
            },
        )
        return await self.action_repository.create_plan(plan)

    async def load_reasoning_run(self, reasoning_run_id: UUID) -> LlmReasoningRun:
        run = await self.reasoning_repository.get_run(reasoning_run_id)
        if run is None:
            raise AppError(404, "reasoning_run_not_found", "Reasoning run not found")
        return run

    async def load_signal(self, signal_id: UUID) -> Signal:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return signal

    async def load_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return run

    async def add_audit_log(
        self,
        analysis_run_id: UUID,
        event_type: str,
        message: str,
        metadata_json: dict[str, object] | None = None,
    ) -> None:
        await self.analysis_repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=analysis_run_id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )


def collect_requested_actions(scenarios: list[ScenarioHypothesis]) -> list[str]:
    actions: list[str] = []
    for scenario in scenarios:
        for action in scenario.suggested_backend_actions_json:
            if isinstance(action, str):
                actions.append(action)
    return actions or [ReasoningActionType.NO_ACTION.value]


def idempotency_key(
    reasoning_run_id: UUID,
    signal_id: UUID,
    action_type: ReasoningActionType,
    horizon_minutes: int | None,
) -> str:
    horizon_part = f":{horizon_minutes}" if horizon_minutes is not None else ""
    return f"reasoning:{reasoning_run_id}:signal:{signal_id}:{action_type.value}{horizon_part}"


def priority_for_action(action_type: ReasoningActionType) -> ReasoningActionPriority:
    if action_type == ReasoningActionType.REQUEST_HUMAN_REVIEW:
        return ReasoningActionPriority.HIGH
    if action_type == ReasoningActionType.NO_ACTION:
        return ReasoningActionPriority.LOW
    return ReasoningActionPriority.NORMAL


def metadata_list(metadata: dict[str, object], key: str) -> list[dict[str, object]]:
    value = metadata.get(key)
    if not isinstance(value, list):
        raise AppError(422, "unsupported_action_type", "Unsupported action type")
    return [item for item in value if isinstance(item, dict)]
