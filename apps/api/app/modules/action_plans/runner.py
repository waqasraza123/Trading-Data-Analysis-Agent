import asyncio
import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.core.time import utc_now
from app.modules.action_plans.executor import ActionExecutionResult, ReasoningActionExecutor
from app.modules.action_plans.models import (
    ReasoningActionItem,
    ReasoningActionItemStatus,
    ReasoningActionWorkerRun,
    ReasoningActionWorkerRunStatus,
)
from app.modules.action_plans.repository import ReasoningActionPlanRepository
from app.modules.analysis.models import AnalysisAuditLog
from app.modules.analysis.repository import AnalysisRepository


@dataclass
class ReasoningActionBatchResult:
    worker_run: ReasoningActionWorkerRun
    items: list[ActionExecutionResult] = field(default_factory=list)

    @property
    def claimed_count(self) -> int:
        return self.worker_run.claimed_count

    @property
    def completed_count(self) -> int:
        return self.worker_run.completed_count

    @property
    def skipped_count(self) -> int:
        return self.worker_run.skipped_count

    @property
    def failed_count(self) -> int:
        return self.worker_run.failed_count


class ReasoningActionRunner:
    def __init__(
        self,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
        session: AsyncSession | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        worker_id: str = "api-request",
    ) -> None:
        self.settings = settings or get_settings()
        self.logger = logger or logging.getLogger(__name__)
        self.session = session
        self.session_factory = session_factory
        self.worker_id = worker_id

    async def execute_due_actions(
        self,
        workspace_id: UUID | None = None,
        limit: int | None = None,
    ) -> ReasoningActionBatchResult:
        batch_limit = limit or self.settings.reasoning_action_worker_batch_size
        if self.session_factory is None:
            if self.session is None:
                msg = "ReasoningActionRunner requires a session or session_factory"
                raise RuntimeError(msg)
            return await self.execute_due_actions_in_session(
                self.session,
                workspace_id,
                batch_limit,
            )
        return await self.execute_due_actions_with_factory(workspace_id, batch_limit)

    async def execute_due_actions_in_session(
        self,
        session: AsyncSession,
        workspace_id: UUID | None,
        batch_limit: int,
    ) -> ReasoningActionBatchResult:
        repository = ReasoningActionPlanRepository(session)
        worker_run, claimed_items = await self.claim_batch(repository, workspace_id, batch_limit)
        await session.commit()
        results: list[ActionExecutionResult] = []
        for item in claimed_items:
            results.append(await self.execute_claimed_item(session, item))
        await self.finish_worker_run(session, worker_run, results)
        await session.commit()
        return ReasoningActionBatchResult(worker_run=worker_run, items=results)

    async def execute_due_actions_with_factory(
        self,
        workspace_id: UUID | None,
        batch_limit: int,
    ) -> ReasoningActionBatchResult:
        if self.session_factory is None:
            msg = "ReasoningActionRunner requires a session_factory"
            raise RuntimeError(msg)
        async with self.session_factory() as session:
            repository = ReasoningActionPlanRepository(session)
            claimed_worker_run, claimed_items = await self.claim_batch(
                repository,
                workspace_id,
                batch_limit,
            )
            claimed_ids = [item.id for item in claimed_items]
            worker_run_id = claimed_worker_run.id
            await session.commit()
        results = await self.execute_claimed_items_concurrently(claimed_ids)
        async with self.session_factory() as session:
            repository = ReasoningActionPlanRepository(session)
            loaded_worker_run = await repository.get_latest_worker_run(worker_id=self.worker_id)
            if loaded_worker_run is None or loaded_worker_run.id != worker_run_id:
                loaded_worker_run = await session.get(ReasoningActionWorkerRun, worker_run_id)
            if loaded_worker_run is None:
                msg = "Reasoning action worker run disappeared during execution"
                raise RuntimeError(msg)
            await self.finish_worker_run(session, loaded_worker_run, results)
            await session.commit()
            return ReasoningActionBatchResult(worker_run=loaded_worker_run, items=results)

    async def claim_batch(
        self,
        repository: ReasoningActionPlanRepository,
        workspace_id: UUID | None,
        batch_limit: int,
    ) -> tuple[ReasoningActionWorkerRun, list[ReasoningActionItem]]:
        now = utc_now()
        await ReasoningActionExecutor(repository.session, settings=self.settings).mark_due_actions(
            workspace_id=workspace_id
        )
        worker_run = await repository.create_empty_worker_run(
            worker_id=self.worker_id,
            workspace_id=workspace_id,
            batch_limit=batch_limit,
            started_at=now,
        )
        claimed_items = await repository.claim_due_items(
            now=now,
            worker_id=self.worker_id,
            workspace_id=workspace_id,
            limit=batch_limit,
            lock_seconds=self.settings.reasoning_action_worker_lock_seconds,
            max_attempts=self.settings.reasoning_action_worker_max_attempts,
        )
        worker_run.claimed_count = len(claimed_items)
        worker_run.metadata_json = {
            "claimedActionItemIds": [str(item.id) for item in claimed_items]
        }
        await repository.update_worker_run(worker_run)
        self.logger.info(
            "reasoning_action_items_claimed",
            extra={"worker_id": self.worker_id, "claimed_count": len(claimed_items)},
        )
        for item in claimed_items:
            await self.audit_item_claimed(repository.session, item)
        return worker_run, claimed_items

    async def execute_claimed_items_concurrently(
        self,
        action_item_ids: list[UUID],
    ) -> list[ActionExecutionResult]:
        if not action_item_ids:
            return []
        semaphore = asyncio.Semaphore(self.settings.reasoning_action_worker_max_concurrency)

        async def run_one(action_item_id: UUID) -> ActionExecutionResult:
            async with semaphore:
                return await self.execute_claimed_item_with_factory(action_item_id)

        return list(await asyncio.gather(*(run_one(item_id) for item_id in action_item_ids)))

    async def execute_claimed_item_with_factory(
        self,
        action_item_id: UUID,
    ) -> ActionExecutionResult:
        if self.session_factory is None:
            msg = "ReasoningActionRunner requires a session_factory"
            raise RuntimeError(msg)
        async with self.session_factory() as session:
            repository = ReasoningActionPlanRepository(session)
            item = await repository.get_item(action_item_id)
            if item is None:
                msg = f"Reasoning action item not found: {action_item_id}"
                raise RuntimeError(msg)
            return await self.execute_claimed_item(session, item)

    async def execute_claimed_item(
        self,
        session: AsyncSession,
        item: ReasoningActionItem,
    ) -> ActionExecutionResult:
        self.logger.info(
            "reasoning_action_item_started",
            extra={
                "worker_id": self.worker_id,
                "action_item_id": str(item.id),
                "action_type": item.action_type,
                "attempt": item.attempts,
            },
        )
        result = await ReasoningActionExecutor(session, settings=self.settings).execute_item(
            item,
            manual=False,
            preclaimed=True,
        )
        self.log_item_result(result)
        return result

    def log_item_result(self, result: ActionExecutionResult) -> None:
        item = result.item
        extra = {
            "worker_id": self.worker_id,
            "action_item_id": str(item.id),
            "action_type": item.action_type,
            "status": item.status,
        }
        if item.status == ReasoningActionItemStatus.COMPLETED.value:
            self.logger.info("reasoning_action_item_completed", extra=extra)
            return
        if item.status == ReasoningActionItemStatus.SKIPPED.value:
            self.logger.info("reasoning_action_item_skipped", extra=extra)
            return
        if item.status == ReasoningActionItemStatus.PENDING.value:
            self.logger.warning("reasoning_action_item_retry_scheduled", extra=extra)
            return
        if item.status == ReasoningActionItemStatus.FAILED.value:
            self.logger.error(
                "reasoning_action_item_max_attempts_reached"
                if item.attempts
                >= min(
                    item.max_attempts,
                    self.settings.reasoning_action_worker_max_attempts,
                )
                else "reasoning_action_item_failed",
                extra={**extra, "error_code": item.error_code},
            )

    async def finish_worker_run(
        self,
        session: AsyncSession,
        worker_run: ReasoningActionWorkerRun,
        results: list[ActionExecutionResult],
    ) -> None:
        repository = ReasoningActionPlanRepository(session)
        completed_count = sum(
            1
            for result in results
            if result.item.status == ReasoningActionItemStatus.COMPLETED.value
        )
        skipped_count = sum(
            1
            for result in results
            if result.item.status
            in {
                ReasoningActionItemStatus.SKIPPED.value,
                ReasoningActionItemStatus.PENDING.value,
            }
        )
        failed_count = sum(
            1 for result in results if result.item.status == ReasoningActionItemStatus.FAILED.value
        )
        worker_run.completed_count = completed_count
        worker_run.skipped_count = skipped_count
        worker_run.failed_count = failed_count
        worker_run.completed_at = utc_now()
        worker_run.status = worker_run_status(completed_count, skipped_count, failed_count)
        worker_run.metadata_json = {
            **worker_run.metadata_json,
            "completedActionItemIds": [
                str(result.item.id)
                for result in results
                if result.item.status == ReasoningActionItemStatus.COMPLETED.value
            ],
            "skippedActionItemIds": [
                str(result.item.id)
                for result in results
                if result.item.status
                in {
                    ReasoningActionItemStatus.SKIPPED.value,
                    ReasoningActionItemStatus.PENDING.value,
                }
            ],
            "failedActionItemIds": [
                str(result.item.id)
                for result in results
                if result.item.status == ReasoningActionItemStatus.FAILED.value
            ],
        }
        await repository.update_worker_run(worker_run)
        self.logger.info(
            "reasoning_action_worker_poll_completed",
            extra={
                "worker_id": self.worker_id,
                "worker_run_id": str(worker_run.id),
                "claimed_count": worker_run.claimed_count,
                "completed_count": completed_count,
                "skipped_count": skipped_count,
                "failed_count": failed_count,
                "status": worker_run.status,
            },
        )

    async def audit_item_claimed(self, session: AsyncSession, item: ReasoningActionItem) -> None:
        if item.analysis_run_id is None:
            return
        await AnalysisRepository(session).add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=item.analysis_run_id,
                event_type="reasoning_action_item_claimed",
                message="Reasoning action item claimed by worker",
                metadata_json={
                    "actionItemId": str(item.id),
                    "actionType": item.action_type,
                    "workerId": self.worker_id,
                },
            )
        )


def worker_run_status(completed_count: int, skipped_count: int, failed_count: int) -> str:
    if failed_count:
        return ReasoningActionWorkerRunStatus.COMPLETED_WITH_WARNINGS.value
    if skipped_count:
        return ReasoningActionWorkerRunStatus.COMPLETED_WITH_WARNINGS.value
    return ReasoningActionWorkerRunStatus.COMPLETED.value
