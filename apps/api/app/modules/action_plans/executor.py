from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.action_plans.models import (
    ReasoningActionItem,
    ReasoningActionItemStatus,
    ReasoningActionType,
)
from app.modules.action_plans.repository import ReasoningActionPlanRepository
from app.modules.analysis.models import AnalysisAuditLog, AnalysisReplayMode, AnalysisRun
from app.modules.analysis.repository import AnalysisRepository
from app.modules.analysis.schemas import AnalysisReplayRequest
from app.modules.analysis.service import AnalysisService
from app.modules.candles.service import CandleService
from app.modules.candles.timeframes import Timeframe, timeframe_duration
from app.modules.news.service import NewsCorrelationService
from app.modules.outcomes.service import OutcomeEvaluationService

AUTOMATIC_DUE_ACTIONS = {
    ReasoningActionType.EVALUATE_OUTCOME_AFTER_HORIZON.value,
    ReasoningActionType.RUN_REPLAY.value,
    ReasoningActionType.RUN_NEWS_CORRELATION.value,
    ReasoningActionType.WAIT_FOR_MORE_FINAL_CANDLES.value,
    ReasoningActionType.NO_ACTION.value,
}


@dataclass(frozen=True)
class ActionExecutionResult:
    item: ReasoningActionItem
    executed: bool
    result: dict[str, object] | None = None


class ReasoningActionExecutor:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.action_repository = ReasoningActionPlanRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.outcome_service = OutcomeEvaluationService(session, settings=self.settings)
        self.analysis_service = AnalysisService(session)
        self.news_correlation_service = NewsCorrelationService(session, settings=self.settings)
        self.candle_service = CandleService(session)

    async def execute_action_item(self, action_item_id: UUID) -> ActionExecutionResult:
        item = await self.action_repository.get_item(action_item_id)
        if item is None:
            raise AppError(404, "action_item_not_found", "Action item not found")
        return await self.execute_item(item, manual=True, preclaimed=False)

    async def execute_due_actions(
        self,
        workspace_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ActionExecutionResult]:
        await self.mark_due_actions(workspace_id=workspace_id)
        due_items = [
            item
            for item in await self.action_repository.list_due_items(
                now=utc_now(),
                workspace_id=workspace_id,
                limit=limit,
            )
            if item.action_type in AUTOMATIC_DUE_ACTIONS
        ][:limit]
        results: list[ActionExecutionResult] = []
        for item in due_items:
            results.append(await self.execute_item(item, manual=False, preclaimed=False))
        return results

    async def list_due_actions(
        self,
        workspace_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ReasoningActionItem]:
        await self.mark_due_actions(workspace_id=workspace_id)
        due_items = await self.action_repository.list_due_items(
            now=utc_now(),
            workspace_id=workspace_id,
            limit=limit,
        )
        return [item for item in due_items if item.action_type in AUTOMATIC_DUE_ACTIONS][:limit]

    async def mark_due_actions(self, workspace_id: UUID | None = None) -> list[ReasoningActionItem]:
        items = await self.action_repository.list_pending_items_to_mark_due(
            now=utc_now(),
            workspace_id=workspace_id,
        )
        marked: list[ReasoningActionItem] = []
        for item in items:
            if item.action_type not in AUTOMATIC_DUE_ACTIONS:
                continue
            item.status = ReasoningActionItemStatus.DUE.value
            marked.append(await self.action_repository.update_item(item))
            await self.add_audit_log(
                item.analysis_run_id,
                "reasoning_action_item_due",
                "Reasoning action item marked due",
                {"actionItemId": str(item.id), "actionType": item.action_type},
            )
        if marked:
            await self.session.commit()
        return marked

    async def execute_item(
        self,
        item: ReasoningActionItem,
        manual: bool,
        preclaimed: bool = False,
    ) -> ActionExecutionResult:
        if item.status in {
            ReasoningActionItemStatus.COMPLETED.value,
            ReasoningActionItemStatus.SKIPPED.value,
            ReasoningActionItemStatus.CANCELLED.value,
        }:
            return ActionExecutionResult(item=item, executed=False, result=item.result_json)
        if item.status == ReasoningActionItemStatus.RUNNING.value and not preclaimed:
            return ActionExecutionResult(
                item=item,
                executed=False,
                result={"reason": "already_running"},
            )
        max_attempts = min(item.max_attempts, self.settings.reasoning_action_worker_max_attempts)
        if (not preclaimed and item.attempts >= max_attempts) or (
            preclaimed and item.attempts > max_attempts
        ):
            item.status = ReasoningActionItemStatus.FAILED.value
            item.error_code = "max_attempts_exceeded"
            item.error_message = "Action item exceeded maximum attempts"
            item.locked_by = None
            item.locked_until = None
            await self.action_repository.update_item(item)
            await self.session.commit()
            return ActionExecutionResult(item=item, executed=False, result=item.result_json)
        if item.action_type == ReasoningActionType.REQUEST_HUMAN_REVIEW.value:
            item.status = ReasoningActionItemStatus.PENDING.value
            item.result_json = {"status": "pending_human_review", "manualExecution": manual}
            item.locked_by = None
            item.locked_until = None
            await self.action_repository.update_item(item)
            await self.session.commit()
            return ActionExecutionResult(item=item, executed=False, result=item.result_json)
        if not preclaimed:
            item.status = ReasoningActionItemStatus.RUNNING.value
            item.attempts += 1
            item.last_attempted_at = utc_now()
            item.error_code = None
            item.error_message = None
            await self.action_repository.update_item(item)
            await self.add_audit_log(
                item.analysis_run_id,
                "reasoning_action_item_started",
                "Reasoning action item execution started",
                {"actionItemId": str(item.id), "actionType": item.action_type},
            )
        try:
            result = await self.dispatch(item)
            if result.get("pending") is True:
                item.status = ReasoningActionItemStatus.PENDING.value
                item.result_json = result
                item.due_at = next_due_at(item)
                item.locked_by = None
                item.locked_until = None
                await self.action_repository.update_item(item)
                await self.session.commit()
                return ActionExecutionResult(item=item, executed=False, result=result)
            item.status = (
                ReasoningActionItemStatus.SKIPPED.value
                if result.get("skipped") is True
                else ReasoningActionItemStatus.COMPLETED.value
            )
            item.result_json = result
            item.completed_at = utc_now()
            item.locked_by = None
            item.locked_until = None
            await self.action_repository.update_item(item)
            await self.add_audit_log(
                item.analysis_run_id,
                (
                    "reasoning_action_item_skipped"
                    if item.status == ReasoningActionItemStatus.SKIPPED.value
                    else "reasoning_action_item_completed"
                ),
                "Reasoning action item execution finished",
                {"actionItemId": str(item.id), "actionType": item.action_type},
            )
            await self.session.commit()
            return ActionExecutionResult(item=item, executed=True, result=result)
        except Exception as error:
            item.status = (
                ReasoningActionItemStatus.FAILED.value
                if item.attempts >= max_attempts
                else ReasoningActionItemStatus.PENDING.value
            )
            item.error_code = error_code(error)
            item.error_message = str(error)[:1000]
            item.result_json = {"failed": True, "errorCode": item.error_code}
            item.locked_by = None
            item.locked_until = None
            if item.status == ReasoningActionItemStatus.PENDING.value:
                item.due_at = retry_due_at()
            await self.action_repository.update_item(item)
            await self.add_audit_log(
                item.analysis_run_id,
                "reasoning_action_item_failed",
                "Reasoning action item execution failed",
                {
                    "actionItemId": str(item.id),
                    "actionType": item.action_type,
                    "errorCode": item.error_code,
                },
            )
            await self.session.commit()
            return ActionExecutionResult(item=item, executed=False, result=item.result_json)

    async def dispatch(self, item: ReasoningActionItem) -> dict[str, object]:
        if item.action_type == ReasoningActionType.EVALUATE_OUTCOME_AFTER_HORIZON.value:
            return await self.execute_outcome_action(item)
        if item.action_type == ReasoningActionType.RUN_REPLAY.value:
            return await self.execute_replay_action(item)
        if item.action_type == ReasoningActionType.RUN_NEWS_CORRELATION.value:
            return await self.execute_news_action(item)
        if item.action_type == ReasoningActionType.WAIT_FOR_MORE_FINAL_CANDLES.value:
            return await self.execute_wait_action(item)
        if item.action_type == ReasoningActionType.NO_ACTION.value:
            return {"skipped": True, "reason": "no_action"}
        raise AppError(422, "unsupported_action_type", "Unsupported action type")

    async def execute_outcome_action(self, item: ReasoningActionItem) -> dict[str, object]:
        if item.signal_id is None or item.horizon_minutes is None:
            raise AppError(
                422,
                "invalid_outcome_action",
                "Outcome action requires signal and horizon",
            )
        analysis_run = await self.load_analysis_run(item.analysis_run_id)
        if not await self.enough_future_candles(analysis_run, item.horizon_minutes):
            return {
                "pending": True,
                "reason": "insufficient_final_candles",
                "horizonMinutes": item.horizon_minutes,
            }
        outcomes = await self.outcome_service.evaluate_signal_outcomes(
            signal_id=item.signal_id,
            horizons_minutes=[item.horizon_minutes],
            force_recompute=False,
        )
        return {
            "outcomeIds": [str(outcome.id) for outcome in outcomes],
            "statuses": [outcome.evaluation_status for outcome in outcomes],
            "horizonsMinutes": [outcome.horizon_minutes for outcome in outcomes],
        }

    async def execute_replay_action(self, item: ReasoningActionItem) -> dict[str, object]:
        analysis_run = await self.load_analysis_run(item.analysis_run_id)
        allow_replay_of_replay = item.input_json.get("allowReplayOfReplay") is True
        if analysis_run.analysis_mode == "replay" and not allow_replay_of_replay:
            return {"skipped": True, "reason": "replay_of_replay_skipped"}
        existing_replays = await self.analysis_repository.list_runs(
            limit=1,
            offset=0,
            workspace_id=analysis_run.workspace_id,
            analysis_mode="replay",
            replayed_from_analysis_run_id=analysis_run.id,
        )
        if existing_replays:
            return {
                "skipped": True,
                "reason": "replay_already_exists",
                "replayAnalysisRunId": str(existing_replays[0].id),
            }
        replay_run = await self.analysis_service.replay_run(
            analysis_run.id,
            AnalysisReplayRequest(mode=AnalysisReplayMode.LATEST_ENGINE_VERSION),
        )
        return {
            "replayAnalysisRunId": str(replay_run.id),
            "status": str(replay_run.status),
            "replayMode": AnalysisReplayMode.LATEST_ENGINE_VERSION.value,
        }

    async def execute_news_action(self, item: ReasoningActionItem) -> dict[str, object]:
        if item.signal_id is None:
            raise AppError(422, "invalid_news_action", "News correlation action requires signal")
        correlations = await self.news_correlation_service.correlate_signal_with_news(
            item.signal_id,
            commit=True,
        )
        return {
            "correlationIds": [str(correlation.id) for correlation in correlations],
            "correlationCount": len(correlations),
        }

    async def execute_wait_action(self, item: ReasoningActionItem) -> dict[str, object]:
        analysis_run = await self.load_analysis_run(item.analysis_run_id)
        enough = await self.enough_future_candles(analysis_run, None)
        if not enough:
            return {"pending": True, "reason": "waiting_for_more_final_candles"}
        return {"finalCandlesAvailable": True}

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

    async def load_analysis_run(self, analysis_run_id: UUID | None) -> AnalysisRun:
        if analysis_run_id is None:
            raise AppError(422, "analysis_run_required", "Action item requires analysis run")
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return run

    async def add_audit_log(
        self,
        analysis_run_id: UUID | None,
        event_type: str,
        message: str,
        metadata_json: dict[str, object] | None = None,
    ) -> None:
        if analysis_run_id is None:
            return
        await self.analysis_repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=analysis_run_id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )


def next_due_at(item: ReasoningActionItem) -> datetime | None:
    if item.action_type != ReasoningActionType.WAIT_FOR_MORE_FINAL_CANDLES.value:
        return item.due_at
    return utc_now() + timeframe_duration(Timeframe("1m"))


def retry_due_at() -> datetime:
    return utc_now() + timeframe_duration(Timeframe("1m"))


def error_code(error: Exception) -> str:
    if isinstance(error, AppError):
        return error.code
    return type(error).__name__
