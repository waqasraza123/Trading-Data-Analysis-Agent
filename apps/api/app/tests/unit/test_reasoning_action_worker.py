from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from app.config import Settings
from app.modules.action_plans import runner as runner_module
from app.modules.action_plans.executor import ActionExecutionResult
from app.modules.action_plans.models import (
    ReasoningActionItem,
    ReasoningActionItemStatus,
    ReasoningActionType,
    ReasoningActionWorkerRun,
    ReasoningActionWorkerRunStatus,
)
from app.modules.action_plans.repository import EXECUTABLE_ACTION_TYPES
from app.modules.action_plans.runner import ReasoningActionRunner
from app.modules.action_plans.service import ReasoningActionPlanService

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
WORKSPACE_ID = uuid4()


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class FakeRepository:
    def __init__(self, session: FakeSession | None = None) -> None:
        self.session = session or FakeSession()
        self.items: list[ReasoningActionItem] = []
        self.worker_runs: list[ReasoningActionWorkerRun] = []

    async def claim_due_items(
        self,
        now: datetime,
        worker_id: str,
        limit: int,
        lock_seconds: int,
        max_attempts: int,
        workspace_id: UUID | None = None,
    ) -> list[ReasoningActionItem]:
        selected: list[ReasoningActionItem] = []
        for item in sorted(self.items, key=lambda row: row.created_at):
            if len(selected) >= limit:
                break
            if item.action_type not in EXECUTABLE_ACTION_TYPES:
                continue
            if workspace_id is not None and item.workspace_id != workspace_id:
                continue
            if item.attempts >= min(item.max_attempts, max_attempts):
                continue
            locked_until = item.locked_until
            has_valid_lock = item.locked_by is not None and locked_until is not None
            if has_valid_lock and locked_until is not None and locked_until > now:
                continue
            is_due = item.status in {
                ReasoningActionItemStatus.PENDING.value,
                ReasoningActionItemStatus.DUE.value,
            } and (item.due_at is None or item.due_at <= now)
            is_expired_running = (
                item.status == ReasoningActionItemStatus.RUNNING.value
                and item.locked_until is not None
                and item.locked_until <= now
            )
            if not is_due and not is_expired_running:
                continue
            item.status = ReasoningActionItemStatus.RUNNING.value
            item.attempts += 1
            item.last_attempted_at = now
            item.locked_by = worker_id
            item.locked_until = now + timedelta(seconds=lock_seconds)
            item.error_code = None
            item.error_message = None
            selected.append(item)
        return selected

    async def create_empty_worker_run(
        self,
        worker_id: str,
        batch_limit: int,
        started_at: datetime,
        workspace_id: UUID | None = None,
    ) -> ReasoningActionWorkerRun:
        run = ReasoningActionWorkerRun(
            id=uuid4(),
            worker_id=worker_id,
            workspace_id=workspace_id,
            status=ReasoningActionWorkerRunStatus.RUNNING.value,
            batch_limit=batch_limit,
            claimed_count=0,
            completed_count=0,
            skipped_count=0,
            failed_count=0,
            started_at=started_at,
            metadata_json={},
        )
        run.created_at = started_at
        self.worker_runs.append(run)
        return run

    async def update_worker_run(
        self,
        run: ReasoningActionWorkerRun,
    ) -> ReasoningActionWorkerRun:
        return run


class FakeExecutor:
    def __init__(self, session: object, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings

    async def mark_due_actions(
        self,
        workspace_id: UUID | None = None,
    ) -> list[ReasoningActionItem]:
        return []

    async def execute_item(
        self,
        item: ReasoningActionItem,
        manual: bool,
        preclaimed: bool = False,
    ) -> ActionExecutionResult:
        mode = item.input_json.get("mode")
        if mode == "skipped":
            item.status = ReasoningActionItemStatus.SKIPPED.value
        elif mode == "retry":
            item.status = ReasoningActionItemStatus.PENDING.value
        elif mode == "failed":
            item.status = ReasoningActionItemStatus.FAILED.value
            item.error_code = "test_failure"
        else:
            item.status = ReasoningActionItemStatus.COMPLETED.value
        item.locked_by = None
        item.locked_until = None
        return ActionExecutionResult(item=item, executed=item.status == "completed", result={})


@pytest.mark.anyio
async def test_claim_due_items_selects_only_due_executable_items() -> None:
    repository = FakeRepository()
    due = action_item(ReasoningActionType.NO_ACTION.value, status="pending", due_at=NOW)
    future = action_item(
        ReasoningActionType.NO_ACTION.value,
        status="pending",
        due_at=NOW + timedelta(minutes=1),
    )
    completed = action_item(ReasoningActionType.NO_ACTION.value, status="completed", due_at=NOW)
    human = action_item(ReasoningActionType.REQUEST_HUMAN_REVIEW.value, status="due", due_at=NOW)
    disallowed = action_item("buy", status="due", due_at=NOW)
    repository.items = [due, future, completed, human, disallowed]

    claimed = await repository.claim_due_items(NOW, "worker-1", 25, 120, 3)

    assert claimed == [due]
    assert due.status == ReasoningActionItemStatus.RUNNING.value
    assert due.attempts == 1


@pytest.mark.anyio
async def test_claim_due_items_respects_limit_and_attempts() -> None:
    repository = FakeRepository()
    first = action_item(ReasoningActionType.NO_ACTION.value, status="due", due_at=NOW)
    second = action_item(ReasoningActionType.NO_ACTION.value, status="due", due_at=NOW)
    maxed = action_item(ReasoningActionType.NO_ACTION.value, status="due", due_at=NOW)
    maxed.attempts = 3
    maxed.max_attempts = 3
    repository.items = [first, second, maxed]

    claimed = await repository.claim_due_items(NOW, "worker-1", 1, 120, 3)

    assert claimed == [first]
    assert second.status == ReasoningActionItemStatus.DUE.value
    assert maxed.status == ReasoningActionItemStatus.DUE.value


@pytest.mark.anyio
async def test_claim_due_items_respects_valid_and_expired_locks() -> None:
    repository = FakeRepository()
    locked = action_item(ReasoningActionType.NO_ACTION.value, status="due", due_at=NOW)
    locked.locked_by = "worker-0"
    locked.locked_until = NOW + timedelta(seconds=30)
    expired = action_item(ReasoningActionType.NO_ACTION.value, status="running", due_at=NOW)
    expired.locked_by = "worker-0"
    expired.locked_until = NOW - timedelta(seconds=1)
    repository.items = [locked, expired]

    claimed = await repository.claim_due_items(NOW, "worker-1", 25, 120, 3)

    assert claimed == [expired]
    assert locked.locked_by == "worker-0"
    assert expired.locked_by == "worker-1"


@pytest.mark.anyio
async def test_worker_run_executes_claimed_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    repository = FakeRepository(session)
    first = action_item(ReasoningActionType.NO_ACTION.value, status="due", due_at=NOW)
    second = action_item(
        ReasoningActionType.WAIT_FOR_MORE_FINAL_CANDLES.value,
        status="due",
        due_at=NOW,
        input_json={"mode": "retry"},
    )
    repository.items = [first, second]
    monkeypatch.setattr(runner_module, "ReasoningActionPlanRepository", lambda _: repository)
    monkeypatch.setattr(runner_module, "ReasoningActionExecutor", FakeExecutor)

    result = await ReasoningActionRunner(
        session=cast(Any, session), settings=Settings(_env_file=None), worker_id="worker-1"
    ).execute_due_actions(limit=25)

    assert result.claimed_count == 2
    assert result.completed_count == 1
    assert result.skipped_count == 1
    assert result.failed_count == 0
    assert session.commit_count == 2


@pytest.mark.anyio
async def test_worker_run_handles_no_due_work(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    repository = FakeRepository(session)
    monkeypatch.setattr(runner_module, "ReasoningActionPlanRepository", lambda _: repository)
    monkeypatch.setattr(runner_module, "ReasoningActionExecutor", FakeExecutor)

    result = await ReasoningActionRunner(
        session=cast(Any, session), settings=Settings(_env_file=None), worker_id="worker-1"
    ).execute_due_actions(limit=25)

    assert result.claimed_count == 0
    assert result.worker_run.status == ReasoningActionWorkerRunStatus.COMPLETED.value


@pytest.mark.anyio
async def test_worker_run_records_skipped_and_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    repository = FakeRepository(session)
    skipped = action_item(
        ReasoningActionType.NO_ACTION.value,
        status="due",
        due_at=NOW,
        input_json={"mode": "skipped"},
    )
    failed = action_item(
        ReasoningActionType.NO_ACTION.value,
        status="due",
        due_at=NOW,
        input_json={"mode": "failed"},
    )
    repository.items = [skipped, failed]
    monkeypatch.setattr(runner_module, "ReasoningActionPlanRepository", lambda _: repository)
    monkeypatch.setattr(runner_module, "ReasoningActionExecutor", FakeExecutor)

    result = await ReasoningActionRunner(
        session=cast(Any, session), settings=Settings(_env_file=None), worker_id="worker-1"
    ).execute_due_actions(limit=25)

    assert result.skipped_count == 1
    assert result.failed_count == 1
    assert result.worker_run.status == ReasoningActionWorkerRunStatus.COMPLETED_WITH_WARNINGS.value


@pytest.mark.anyio
async def test_execute_due_service_uses_runner_path(monkeypatch: pytest.MonkeyPatch) -> None:
    item = action_item(ReasoningActionType.NO_ACTION.value, status="completed", due_at=NOW)
    worker_run = ReasoningActionWorkerRun(
        id=uuid4(),
        worker_id="api-execute-due",
        workspace_id=None,
        status=ReasoningActionWorkerRunStatus.COMPLETED.value,
        batch_limit=10,
        claimed_count=1,
        completed_count=1,
        skipped_count=0,
        failed_count=0,
        started_at=NOW,
        metadata_json={},
    )
    worker_run.created_at = NOW

    class FakeRunner:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        async def execute_due_actions(
            self,
            workspace_id: UUID | None = None,
            limit: int | None = None,
        ) -> runner_module.ReasoningActionBatchResult:
            return runner_module.ReasoningActionBatchResult(
                worker_run=worker_run,
                items=[ActionExecutionResult(item=item, executed=True, result={})],
            )

    monkeypatch.setattr("app.modules.action_plans.service.ReasoningActionRunner", FakeRunner)

    response = await ReasoningActionPlanService(cast(Any, FakeSession())).execute_due_actions(
        limit=10
    )

    assert response.executed_count == 1
    assert response.failed_count == 0


def action_item(
    action_type: str,
    status: str,
    due_at: datetime | None,
    input_json: dict[str, object] | None = None,
) -> ReasoningActionItem:
    item = ReasoningActionItem(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        action_plan_id=uuid4(),
        source_type="reasoning_run",
        source_id=uuid4(),
        signal_id=uuid4(),
        analysis_run_id=None,
        reasoning_run_id=uuid4(),
        action_type=action_type,
        status=status,
        priority="normal",
        due_at=due_at,
        horizon_minutes=None,
        idempotency_key=f"test:{uuid4()}",
        input_json=input_json or {},
        result_json=None,
        attempts=0,
        max_attempts=3,
        last_attempted_at=None,
        locked_by=None,
        locked_until=None,
        completed_at=None,
    )
    item.created_at = due_at or NOW
    item.updated_at = item.created_at
    return item
