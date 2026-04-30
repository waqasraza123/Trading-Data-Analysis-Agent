from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.config import Settings
from app.modules.action_plans.executor import ReasoningActionExecutor
from app.modules.action_plans.models import (
    ActionPlanStatus,
    ReasoningActionItem,
    ReasoningActionItemStatus,
    ReasoningActionPlan,
    ReasoningActionType,
)
from app.modules.action_plans.planner import ReasoningActionPlanner
from app.modules.analysis.models import (
    AnalysisAuditLog,
    AnalysisMode,
    AnalysisRun,
    AnalysisRunStatus,
)
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalBias,
    SignalClassificationStatus,
    SignalConfidenceLabel,
)

BASE_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class FakeActionRepository:
    def __init__(self, existing_keys: set[str] | None = None) -> None:
        self.plans: list[ReasoningActionPlan] = []
        self.items: list[ReasoningActionItem] = []
        self.existing_keys = existing_keys or set()

    async def get_latest_by_reasoning_run_id(
        self,
        reasoning_run_id: UUID,
    ) -> ReasoningActionPlan | None:
        return None

    async def list_items(self, action_plan_id: UUID) -> list[ReasoningActionItem]:
        return [item for item in self.items if item.action_plan_id == action_plan_id]

    async def create_plan(self, plan: ReasoningActionPlan) -> ReasoningActionPlan:
        now = datetime.now(UTC)
        plan.created_at = now
        plan.updated_at = now
        self.plans.append(plan)
        return plan

    async def get_item_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str,
    ) -> ReasoningActionItem | None:
        if idempotency_key in self.existing_keys:
            return action_item(idempotency_key=idempotency_key)
        for item in self.items:
            if item.workspace_id == workspace_id and item.idempotency_key == idempotency_key:
                return item
        return None

    async def create_item(self, item: ReasoningActionItem) -> ReasoningActionItem:
        now = datetime.now(UTC)
        item.created_at = now
        item.updated_at = now
        self.items.append(item)
        return item

    async def update_plan(self, plan: ReasoningActionPlan) -> ReasoningActionPlan:
        plan.updated_at = datetime.now(UTC)
        return plan

    async def get_item(self, item_id: UUID) -> ReasoningActionItem | None:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    async def update_item(self, item: ReasoningActionItem) -> ReasoningActionItem:
        item.updated_at = datetime.now(UTC)
        return item

    async def list_due_items(
        self,
        now: datetime,
        limit: int,
        workspace_id: UUID | None = None,
    ) -> list[ReasoningActionItem]:
        return self.items[:limit]

    async def list_pending_items_to_mark_due(
        self,
        now: datetime,
        workspace_id: UUID | None = None,
    ) -> list[ReasoningActionItem]:
        return [
            item for item in self.items if item.status == ReasoningActionItemStatus.PENDING.value
        ]


class FakeReasoningRepository:
    def __init__(self, run: LlmReasoningRun, scenarios: list[ScenarioHypothesis]) -> None:
        self.run = run
        self.scenarios = scenarios

    async def get_run(self, reasoning_run_id: UUID) -> LlmReasoningRun | None:
        return self.run if reasoning_run_id == self.run.id else None

    async def list_scenarios(self, reasoning_run_id: UUID) -> list[ScenarioHypothesis]:
        return self.scenarios if reasoning_run_id == self.run.id else []


class FakeSignalRepository:
    def __init__(self, signal: Signal) -> None:
        self.signal = signal

    async def get_by_id(self, signal_id: UUID) -> Signal | None:
        return self.signal if signal_id == self.signal.id else None


class FakeAnalysisRepository:
    def __init__(self, run: AnalysisRun, existing_replays: list[AnalysisRun] | None = None) -> None:
        self.run = run
        self.existing_replays = existing_replays or []
        self.audit_events: list[str] = []

    async def get_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return self.run if analysis_run_id == self.run.id else None

    async def list_runs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        symbol_id: UUID | None = None,
        status: str | None = None,
        analysis_mode: str | None = None,
        replayed_from_analysis_run_id: UUID | None = None,
    ) -> list[AnalysisRun]:
        return self.existing_replays[:limit]

    async def add_audit_log(self, audit_log: AnalysisAuditLog) -> AnalysisAuditLog:
        self.audit_events.append(audit_log.event_type)
        return audit_log


class FakeOutcomeRepository:
    def __init__(self, existing_horizons: set[int] | None = None) -> None:
        self.existing_horizons = existing_horizons or set()

    async def get_outcome(
        self,
        signal_id: UUID,
        horizon_minutes: int,
        evaluation_version: str,
    ) -> SimpleNamespace | None:
        if horizon_minutes not in self.existing_horizons:
            return None
        return SimpleNamespace(id=uuid4(), horizon_minutes=horizon_minutes)


class FakeNewsCorrelationRepository:
    def __init__(self, count: int = 0) -> None:
        self.count = count

    async def list_by_signal_id(self, signal_id: UUID) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=uuid4()) for _ in range(self.count)]


class FakeCandleService:
    def __init__(self, count: int) -> None:
        self.count = count

    async def fetch_candle_window(self, **kwargs: object) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=uuid4()) for _ in range(self.count)]


class FakeOutcomeService:
    def __init__(self) -> None:
        self.calls: list[list[int] | None] = []

    async def evaluate_signal_outcomes(
        self,
        signal_id: UUID,
        horizons_minutes: list[int] | None = None,
        force_recompute: bool = False,
    ) -> list[SimpleNamespace]:
        self.calls.append(horizons_minutes)
        return [
            SimpleNamespace(
                id=uuid4(),
                evaluation_status="evaluated",
                horizon_minutes=horizon,
            )
            for horizon in horizons_minutes or []
        ]


class FakeAnalysisService:
    def __init__(self) -> None:
        self.calls = 0

    async def replay_run(self, analysis_run_id: UUID, payload: object) -> AnalysisRun:
        self.calls += 1
        replay = analysis_run()
        replay.id = uuid4()
        replay.status = AnalysisRunStatus.COMPLETED.value
        replay.replayed_from_analysis_run_id = analysis_run_id
        replay.analysis_mode = AnalysisMode.REPLAY.value
        return replay


class FakeNewsService:
    def __init__(self) -> None:
        self.calls = 0

    async def correlate_signal_with_news(
        self,
        signal_id: UUID,
        commit: bool = False,
    ) -> list[SimpleNamespace]:
        self.calls += 1
        return [SimpleNamespace(id=uuid4())]


@pytest.mark.anyio
async def test_planner_creates_outcome_action_from_scenario() -> None:
    planner, reasoning_run, repository = fake_planner(["evaluate_outcome_after_horizon"])

    result = await planner.build_plan_from_reasoning_run(reasoning_run.id)

    outcome_items = [
        item
        for item in result.items
        if item.action_type == ReasoningActionType.EVALUATE_OUTCOME_AFTER_HORIZON.value
    ]
    assert len(outcome_items) == 4
    assert result.plan.status == ActionPlanStatus.ACTIVE.value
    assert len(repository.items) == 4


@pytest.mark.anyio
async def test_planner_creates_replay_action_from_scenario() -> None:
    planner, reasoning_run, _repository = fake_planner(["run_replay"])

    result = await planner.build_plan_from_reasoning_run(reasoning_run.id)

    assert result.items[0].action_type == ReasoningActionType.RUN_REPLAY.value
    assert result.items[0].input_json["replayMode"] == "latest_engine_version"


@pytest.mark.anyio
async def test_planner_creates_news_correlation_action_from_scenario() -> None:
    planner, reasoning_run, _repository = fake_planner(["run_news_correlation"])

    result = await planner.build_plan_from_reasoning_run(reasoning_run.id)

    assert result.items[0].action_type == ReasoningActionType.RUN_NEWS_CORRELATION.value


@pytest.mark.anyio
async def test_planner_creates_wait_action_from_scenario() -> None:
    planner, reasoning_run, _repository = fake_planner(["wait_for_more_final_candles"])

    result = await planner.build_plan_from_reasoning_run(reasoning_run.id)

    assert result.items[0].action_type == ReasoningActionType.WAIT_FOR_MORE_FINAL_CANDLES.value


@pytest.mark.anyio
async def test_planner_creates_human_review_action_from_scenario() -> None:
    planner, reasoning_run, _repository = fake_planner(["request_human_review"])

    result = await planner.build_plan_from_reasoning_run(reasoning_run.id)

    assert result.items[0].action_type == ReasoningActionType.REQUEST_HUMAN_REVIEW.value


@pytest.mark.anyio
async def test_planner_rejects_trading_action() -> None:
    planner, reasoning_run, _repository = fake_planner(["buy"])

    result = await planner.build_plan_from_reasoning_run(reasoning_run.id)

    assert result.rejected_actions[0]["reason"] == "trading_action_rejected"
    assert result.items[0].action_type == ReasoningActionType.REQUEST_HUMAN_REVIEW.value


@pytest.mark.anyio
async def test_planner_avoids_duplicate_idempotency_keys() -> None:
    existing_key = (
        f"reasoning:{REASONING_RUN_ID}:signal:{SIGNAL_ID}:evaluate_outcome_after_horizon:5"
    )
    planner, reasoning_run, _repository = fake_planner(
        ["evaluate_outcome_after_horizon"],
        existing_keys={existing_key},
    )

    result = await planner.build_plan_from_reasoning_run(reasoning_run.id)

    assert len(result.items) == 3
    assert any(item["reason"] == "duplicate_idempotency_key" for item in result.skipped_actions)


@pytest.mark.anyio
async def test_planner_skips_existing_outcome_horizon() -> None:
    planner, reasoning_run, _repository = fake_planner(
        ["evaluate_outcome_after_horizon"],
        existing_horizons={5},
    )

    result = await planner.build_plan_from_reasoning_run(reasoning_run.id)

    assert {item.horizon_minutes for item in result.items} == {15, 30, 60}
    assert any(item["reason"] == "outcome_exists" for item in result.skipped_actions)


@pytest.mark.anyio
async def test_planner_marks_past_due_outcome_action_as_due() -> None:
    planner, reasoning_run, _repository = fake_planner(["evaluate_outcome_after_horizon"])

    result = await planner.build_plan_from_reasoning_run(reasoning_run.id)

    assert result.items[0].status == ReasoningActionItemStatus.DUE.value


@pytest.mark.anyio
async def test_executor_dispatches_outcome_evaluation() -> None:
    executor, item, services = fake_executor(
        ReasoningActionType.EVALUATE_OUTCOME_AFTER_HORIZON.value,
        horizon_minutes=5,
    )

    result = await executor.execute_action_item(item.id)

    assert result.executed is True
    assert services["outcome"].calls == [[5]]
    assert item.status == ReasoningActionItemStatus.COMPLETED.value


@pytest.mark.anyio
async def test_executor_dispatches_replay() -> None:
    executor, item, services = fake_executor(ReasoningActionType.RUN_REPLAY.value)

    result = await executor.execute_action_item(item.id)

    assert result.executed is True
    assert services["analysis"].calls == 1
    assert item.result_json is not None
    assert "replayAnalysisRunId" in item.result_json


@pytest.mark.anyio
async def test_executor_dispatches_news_correlation() -> None:
    executor, item, services = fake_executor(ReasoningActionType.RUN_NEWS_CORRELATION.value)

    result = await executor.execute_action_item(item.id)

    assert result.executed is True
    assert services["news"].calls == 1
    assert item.result_json is not None
    assert item.result_json["correlationCount"] == 1
    correlation_ids = item.result_json["correlationIds"]
    assert isinstance(correlation_ids, list)
    assert len(correlation_ids) == 1


@pytest.mark.anyio
async def test_executor_keeps_human_review_pending() -> None:
    executor, item, _services = fake_executor(ReasoningActionType.REQUEST_HUMAN_REVIEW.value)

    result = await executor.execute_action_item(item.id)

    assert result.executed is False
    assert item.status == ReasoningActionItemStatus.PENDING.value


@pytest.mark.anyio
async def test_executor_fails_safely_on_unsupported_action() -> None:
    executor, item, _services = fake_executor("buy")

    result = await executor.execute_action_item(item.id)

    assert result.executed is False
    assert item.error_code == "unsupported_action_type"


@pytest.mark.anyio
async def test_execute_due_respects_limit() -> None:
    executor, item, _services = fake_executor(ReasoningActionType.NO_ACTION.value)
    second = action_item(action_type=ReasoningActionType.NO_ACTION.value)
    third = action_item(action_type=ReasoningActionType.NO_ACTION.value)
    executor_any: Any = executor
    repository: Any = executor_any.action_repository
    repository.items = [item, second, third]

    results = await executor.execute_due_actions(limit=2)

    assert len(results) == 2


@pytest.mark.anyio
async def test_executor_respects_max_attempts() -> None:
    executor, item, _services = fake_executor(ReasoningActionType.NO_ACTION.value)
    item.attempts = item.max_attempts

    result = await executor.execute_action_item(item.id)

    assert result.executed is False
    assert item.status == ReasoningActionItemStatus.FAILED.value
    assert item.error_code == "max_attempts_exceeded"


SIGNAL_ID = uuid4()
ANALYSIS_RUN_ID = uuid4()
REASONING_RUN_ID = uuid4()
WORKSPACE_ID = uuid4()


def fake_planner(
    actions: list[str],
    existing_horizons: set[int] | None = None,
    existing_keys: set[str] | None = None,
) -> tuple[ReasoningActionPlanner, LlmReasoningRun, FakeActionRepository]:
    signal = signal_row()
    run = analysis_run()
    reasoning_run = reasoning_run_row(signal, run)
    repository = FakeActionRepository(existing_keys=existing_keys)
    planner = ReasoningActionPlanner.__new__(ReasoningActionPlanner)
    planner_any: Any = planner
    planner_any.session = FakeSession()
    planner_any.settings = Settings(
        _env_file=None,
        outcome_default_horizons_minutes=[5, 15, 30, 60],
        outcome_min_future_candles=3,
        outcome_evaluation_version="v1",
    )
    planner_any.action_repository = repository
    planner_any.reasoning_repository = FakeReasoningRepository(
        reasoning_run,
        [scenario(actions, reasoning_run, signal, run)],
    )
    planner_any.signal_repository = FakeSignalRepository(signal)
    planner_any.analysis_repository = FakeAnalysisRepository(run)
    planner_any.outcome_repository = FakeOutcomeRepository(existing_horizons)
    planner_any.news_correlation_repository = FakeNewsCorrelationRepository()
    planner_any.candle_service = FakeCandleService(count=3)
    return planner, reasoning_run, repository


def fake_executor(
    action_type: str,
    horizon_minutes: int | None = None,
) -> tuple[ReasoningActionExecutor, ReasoningActionItem, dict[str, Any]]:
    session = FakeSession()
    repository = FakeActionRepository()
    item = action_item(action_type=action_type, horizon_minutes=horizon_minutes)
    repository.items.append(item)
    run = analysis_run()
    outcome_service = FakeOutcomeService()
    analysis_service = FakeAnalysisService()
    news_service = FakeNewsService()
    executor = ReasoningActionExecutor.__new__(ReasoningActionExecutor)
    executor_any: Any = executor
    executor_any.session = session
    executor_any.settings = Settings(_env_file=None, outcome_min_future_candles=3)
    executor_any.action_repository = repository
    executor_any.analysis_repository = FakeAnalysisRepository(run)
    executor_any.outcome_service = outcome_service
    executor_any.analysis_service = analysis_service
    executor_any.news_correlation_service = news_service
    executor_any.candle_service = FakeCandleService(count=3)
    return (
        executor,
        item,
        {
            "outcome": outcome_service,
            "analysis": analysis_service,
            "news": news_service,
        },
    )


def signal_row() -> Signal:
    return Signal(
        id=SIGNAL_ID,
        analysis_run_id=ANALYSIS_RUN_ID,
        workspace_id=WORKSPACE_ID,
        symbol_id=uuid4(),
        timeframe="1m",
        bias=SignalBias.BULLISH.value,
        classification_status=SignalClassificationStatus.SIGNAL.value,
        confidence_score=Decimal("0.8000"),
        confidence_label=SignalConfidenceLabel.HIGH.value,
        strategy_profile_key="default",
        strategy_profile_version="v1",
        pattern_type="breakout",
        summary="Stored signal summary.",
    )


def analysis_run() -> AnalysisRun:
    return AnalysisRun(
        id=ANALYSIS_RUN_ID,
        workspace_id=WORKSPACE_ID,
        user_id=None,
        symbol_id=uuid4(),
        source_id=None,
        timeframe="1m",
        start_time=BASE_TIME - timedelta(minutes=15),
        end_time=BASE_TIME,
        analysis_mode=AnalysisMode.HISTORICAL.value,
        include_partial_live_candle=False,
        include_news_correlation=False,
        include_ai_explanation=False,
        status=AnalysisRunStatus.COMPLETED.value,
        engine_version="test",
        rule_set_version="test",
    )


def reasoning_run_row(signal: Signal, run: AnalysisRun) -> LlmReasoningRun:
    return LlmReasoningRun(
        id=REASONING_RUN_ID,
        workspace_id=signal.workspace_id,
        analysis_run_id=run.id,
        signal_id=signal.id,
        outcome_id=None,
        source_type="signal",
        provider="mock",
        model="mock-scenario-v1",
        prompt_version="scenario_reasoning_v1",
        reasoning_type="next_scenarios",
        status="completed",
        input_snapshot_json={},
        output_json={},
        output_text=None,
        safety_status="passed",
        grounding_status="grounded",
        blocked_terms_json=[],
        grounding_issues_json=[],
    )


def scenario(
    actions: list[str],
    reasoning_run: LlmReasoningRun,
    signal: Signal,
    run: AnalysisRun,
) -> ScenarioHypothesis:
    return ScenarioHypothesis(
        id=uuid4(),
        reasoning_run_id=reasoning_run.id,
        workspace_id=signal.workspace_id,
        analysis_run_id=run.id,
        signal_id=signal.id,
        scenario_type="continuation",
        scenario_label="Scenario",
        possibility_label="medium",
        supporting_evidence_json=[],
        conflicting_evidence_json=[],
        outcome_history_json=None,
        next_observations_json=[],
        suggested_backend_actions_json=actions,
        risk_notes_json=[],
        sort_order=0,
    )


def action_item(
    action_type: str = ReasoningActionType.NO_ACTION.value,
    horizon_minutes: int | None = None,
    idempotency_key: str | None = None,
) -> ReasoningActionItem:
    now = datetime.now(UTC)
    item = ReasoningActionItem(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        action_plan_id=uuid4(),
        source_type="reasoning_run",
        source_id=REASONING_RUN_ID,
        signal_id=SIGNAL_ID,
        analysis_run_id=ANALYSIS_RUN_ID,
        reasoning_run_id=REASONING_RUN_ID,
        action_type=action_type,
        status=ReasoningActionItemStatus.DUE.value,
        priority="normal",
        due_at=BASE_TIME,
        horizon_minutes=horizon_minutes,
        idempotency_key=idempotency_key or f"test:{uuid4()}",
        input_json={},
        attempts=0,
        max_attempts=3,
    )
    item.created_at = now
    item.updated_at = now
    return item
