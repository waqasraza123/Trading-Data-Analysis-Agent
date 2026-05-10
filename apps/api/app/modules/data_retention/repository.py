from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.data_retention.models import (
    DataRetentionActionType,
    DataRetentionPolicy,
    DataRetentionPolicyStatus,
    DataRetentionRun,
    DataRetentionRunItem,
    DataRetentionRunItemStatus,
    DataRetentionTargetType,
)
from app.modules.data_retention.planner import PlannedRetentionAction, RetentionTargetPlan
from app.modules.imports.models import ImportBatch
from app.modules.live.models import LiveFeedEvent
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.reasoning.models import LlmReasoningRun


class DataRetentionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_policy(self, policy: DataRetentionPolicy) -> DataRetentionPolicy:
        self.session.add(policy)
        await self.session.flush()
        await self.session.refresh(policy)
        return policy

    async def list_policies(
        self,
        workspace_id: UUID,
        status: DataRetentionPolicyStatus | None,
        limit: int,
        offset: int,
    ) -> list[DataRetentionPolicy]:
        statement: Select[tuple[DataRetentionPolicy]] = (
            select(DataRetentionPolicy)
            .where(DataRetentionPolicy.workspace_id == workspace_id)
            .order_by(DataRetentionPolicy.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(DataRetentionPolicy.status == status.value)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_policy(self, policy_id: UUID) -> DataRetentionPolicy | None:
        return await self.session.get(DataRetentionPolicy, policy_id)

    async def update_policy(self, policy: DataRetentionPolicy) -> DataRetentionPolicy:
        await self.session.flush()
        await self.session.refresh(policy)
        return policy

    async def create_run(self, run: DataRetentionRun) -> DataRetentionRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> DataRetentionRun | None:
        return await self.session.get(DataRetentionRun, run_id)

    async def update_run(self, run: DataRetentionRun) -> DataRetentionRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def create_run_items(
        self,
        run_id: UUID,
        workspace_id: UUID,
        actions: Iterable[PlannedRetentionAction],
    ) -> list[DataRetentionRunItem]:
        items = [
            DataRetentionRunItem(
                workspace_id=workspace_id,
                retention_run_id=run_id,
                target_type=action.target_type.value,
                target_id=action.target_id,
                action_type=action.action_type.value,
                status=DataRetentionRunItemStatus.PLANNED.value,
                reason=action.reason,
                metadata_json=action.metadata,
            )
            for action in actions
        ]
        if not items:
            return []
        self.session.add_all(items)
        await self.session.flush()
        return items

    async def list_run_items(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[DataRetentionRunItem]:
        statement: Select[tuple[DataRetentionRunItem]] = (
            select(DataRetentionRunItem)
            .where(DataRetentionRunItem.retention_run_id == run_id)
            .order_by(DataRetentionRunItem.created_at.asc(), DataRetentionRunItem.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_planned_run_items(self, run_id: UUID) -> list[DataRetentionRunItem]:
        statement: Select[tuple[DataRetentionRunItem]] = (
            select(DataRetentionRunItem)
            .where(
                DataRetentionRunItem.retention_run_id == run_id,
                DataRetentionRunItem.status == DataRetentionRunItemStatus.PLANNED.value,
            )
            .order_by(DataRetentionRunItem.created_at.asc(), DataRetentionRunItem.id.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_run_items_by_status(self, run_id: UUID) -> dict[str, int]:
        statement = (
            select(DataRetentionRunItem.status, func.count())
            .where(DataRetentionRunItem.retention_run_id == run_id)
            .group_by(DataRetentionRunItem.status)
        )
        result = await self.session.execute(statement)
        return {str(status): int(count) for status, count in result.all()}

    async def plan_actions(
        self,
        workspace_id: UUID,
        plans: list[RetentionTargetPlan],
        limit_per_target_type: int,
    ) -> list[PlannedRetentionAction]:
        actions: list[PlannedRetentionAction] = []
        for plan in plans:
            actions.extend(
                await self._plan_known_actions(
                    workspace_id=workspace_id,
                    plan=plan,
                    limit=limit_per_target_type,
                )
            )
        return actions

    async def apply_item(self, item: DataRetentionRunItem) -> DataRetentionRunItem:
        action_type = DataRetentionActionType(item.action_type)
        target_type = DataRetentionTargetType(item.target_type)
        if action_type != DataRetentionActionType.REDACT_PAYLOAD:
            return await self._skip_item(item, "action is not safely applicable in this phase")
        if target_type == DataRetentionTargetType.LIVE_FEED_EVENT:
            return await self._redact_live_feed_event(item)
        if target_type == DataRetentionTargetType.LLM_EXPLANATION_PAYLOAD:
            return await self._redact_llm_explanation(item)
        if target_type == DataRetentionTargetType.REASONING_RUN_PAYLOAD:
            return await self._redact_reasoning_run(item)
        if target_type == DataRetentionTargetType.CHART_SCREENSHOT_AUDIT_PAYLOAD:
            return await self._redact_chart_screenshot_run(item)
        return await self._skip_item(
            item, "target type has no safe redaction adapter in this phase"
        )

    async def _plan_known_actions(
        self,
        workspace_id: UUID,
        plan: RetentionTargetPlan,
        limit: int,
    ) -> list[PlannedRetentionAction]:
        if plan.target_type == DataRetentionTargetType.IMPORT_BATCH:
            return await self._plan_import_batches(workspace_id, plan, limit)
        if plan.target_type == DataRetentionTargetType.LIVE_FEED_EVENT:
            return await self._plan_live_feed_events(workspace_id, plan, limit)
        if plan.target_type == DataRetentionTargetType.LLM_EXPLANATION_PAYLOAD:
            return await self._plan_llm_explanations(workspace_id, plan, limit)
        if plan.target_type == DataRetentionTargetType.REASONING_RUN_PAYLOAD:
            return await self._plan_reasoning_runs(workspace_id, plan, limit)
        if plan.target_type == DataRetentionTargetType.CHART_SCREENSHOT_AUDIT_PAYLOAD:
            return await self._plan_chart_screenshot_runs(workspace_id, plan, limit)
        return await self._plan_optional_table(workspace_id, plan, limit)

    async def _plan_import_batches(
        self,
        workspace_id: UUID,
        plan: RetentionTargetPlan,
        limit: int,
    ) -> list[PlannedRetentionAction]:
        statement: Select[tuple[ImportBatch]] = (
            select(ImportBatch)
            .where(ImportBatch.workspace_id == workspace_id, ImportBatch.created_at < plan.cutoff)
            .order_by(ImportBatch.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            self._action(
                plan=plan,
                target_id=batch.id,
                metadata={
                    "createdAt": batch.created_at.isoformat(),
                    "status": batch.status,
                    "rowsReceived": batch.rows_received,
                    "rowsValid": batch.rows_valid,
                    "rowsInvalid": batch.rows_invalid,
                    "safeApply": False,
                },
            )
            for batch in result.scalars().all()
        ]

    async def _plan_live_feed_events(
        self,
        workspace_id: UUID,
        plan: RetentionTargetPlan,
        limit: int,
    ) -> list[PlannedRetentionAction]:
        statement: Select[tuple[LiveFeedEvent]] = (
            select(LiveFeedEvent)
            .where(
                LiveFeedEvent.workspace_id == workspace_id,
                LiveFeedEvent.created_at < plan.cutoff,
                LiveFeedEvent.payload_json != {},
            )
            .order_by(LiveFeedEvent.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            self._action(
                plan=plan,
                target_id=event.id,
                metadata={
                    "createdAt": event.created_at.isoformat(),
                    "receivedAt": event.received_at.isoformat(),
                    "eventType": event.event_type,
                    "provider": event.provider,
                    "targetFields": ["payload_json"],
                },
            )
            for event in result.scalars().all()
        ]

    async def _plan_llm_explanations(
        self,
        workspace_id: UUID,
        plan: RetentionTargetPlan,
        limit: int,
    ) -> list[PlannedRetentionAction]:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(
                LlmExplanation.workspace_id == workspace_id, LlmExplanation.created_at < plan.cutoff
            )
            .order_by(LlmExplanation.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            self._action(
                plan=plan,
                target_id=explanation.id,
                metadata={
                    "createdAt": explanation.created_at.isoformat(),
                    "provider": explanation.provider,
                    "model": explanation.model,
                    "targetFields": ["input_json", "output_text"],
                },
            )
            for explanation in result.scalars().all()
        ]

    async def _plan_reasoning_runs(
        self,
        workspace_id: UUID,
        plan: RetentionTargetPlan,
        limit: int,
    ) -> list[PlannedRetentionAction]:
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(
                LlmReasoningRun.workspace_id == workspace_id,
                LlmReasoningRun.created_at < plan.cutoff,
            )
            .order_by(LlmReasoningRun.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            self._action(
                plan=plan,
                target_id=run.id,
                metadata={
                    "createdAt": run.created_at.isoformat(),
                    "provider": run.provider,
                    "model": run.model,
                    "targetFields": ["input_snapshot_json", "output_json", "output_text"],
                },
            )
            for run in result.scalars().all()
        ]

    async def _plan_chart_screenshot_runs(
        self,
        workspace_id: UUID,
        plan: RetentionTargetPlan,
        limit: int,
    ) -> list[PlannedRetentionAction]:
        statement: Select[tuple[ChartScreenshotRun]] = (
            select(ChartScreenshotRun)
            .where(
                ChartScreenshotRun.workspace_id == workspace_id,
                ChartScreenshotRun.created_at < plan.cutoff,
            )
            .order_by(ChartScreenshotRun.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            self._action(
                plan=plan,
                target_id=run.id,
                metadata={
                    "createdAt": run.created_at.isoformat(),
                    "status": run.status,
                    "targetFields": ["extracted_payload_json", "parser_metadata_json.ocr"],
                },
            )
            for run in result.scalars().all()
            if run.extracted_payload_json is not None or "ocr" in run.parser_metadata_json
        ]

    async def _plan_optional_table(
        self,
        workspace_id: UUID,
        plan: RetentionTargetPlan,
        limit: int,
    ) -> list[PlannedRetentionAction]:
        table_name = self._optional_table_name(plan.target_type)
        if table_name is None or not await self._table_exists(table_name):
            return []
        rows = await self._select_optional_rows(table_name, workspace_id, plan.cutoff, limit)
        return [
            self._action(
                plan=plan,
                target_id=row["id"],
                metadata={
                    "createdAt": row["created_at"].isoformat(),
                    "tableName": table_name,
                    "safeApply": False,
                },
            )
            for row in rows
        ]

    async def _table_exists(self, table_name: str) -> bool:
        result = await self.session.execute(
            text("select to_regclass(:table_name) is not null"),
            {"table_name": table_name},
        )
        return bool(result.scalar_one())

    async def _select_optional_rows(
        self,
        table_name: str,
        workspace_id: UUID,
        cutoff: datetime,
        limit: int,
    ) -> list[dict[str, object]]:
        statement = text(
            f"select id, created_at from {table_name} "
            "where workspace_id = :workspace_id and created_at < :cutoff "
            "order by created_at asc limit :limit"
        )
        result = await self.session.execute(
            statement,
            {"workspace_id": workspace_id, "cutoff": cutoff, "limit": limit},
        )
        return [dict(row._mapping) for row in result.all()]

    def _action(
        self,
        plan: RetentionTargetPlan,
        target_id: UUID,
        metadata: dict[str, object],
    ) -> PlannedRetentionAction:
        return PlannedRetentionAction(
            target_type=plan.target_type,
            target_id=target_id,
            action_type=plan.action_type,
            reason=plan.reason,
            metadata={**plan.metadata, **metadata},
        )

    def _optional_table_name(self, target_type: DataRetentionTargetType) -> str | None:
        names = {
            DataRetentionTargetType.PROVIDER_POLLING_REQUEST: "provider_polling_requests",
            DataRetentionTargetType.DATASET_EXPORT: "dataset_exports",
            DataRetentionTargetType.WEBHOOK_OUTBOX_EVENT: "webhook_outbox_events",
        }
        return names.get(target_type)

    async def _redact_live_feed_event(self, item: DataRetentionRunItem) -> DataRetentionRunItem:
        result = await self.session.execute(
            update(LiveFeedEvent)
            .where(
                LiveFeedEvent.id == item.target_id,
                LiveFeedEvent.workspace_id == item.workspace_id,
            )
            .values(payload_json=self._redacted_payload(item))
        )
        return await self._mark_mutation_result(item, int(result.rowcount or 0))

    async def _redact_llm_explanation(self, item: DataRetentionRunItem) -> DataRetentionRunItem:
        result = await self.session.execute(
            update(LlmExplanation)
            .where(
                LlmExplanation.id == item.target_id,
                LlmExplanation.workspace_id == item.workspace_id,
            )
            .values(
                input_json=self._redacted_payload(item),
                output_text="[redacted by retention policy]",
            )
        )
        return await self._mark_mutation_result(item, int(result.rowcount or 0))

    async def _redact_reasoning_run(self, item: DataRetentionRunItem) -> DataRetentionRunItem:
        result = await self.session.execute(
            update(LlmReasoningRun)
            .where(
                LlmReasoningRun.id == item.target_id,
                LlmReasoningRun.workspace_id == item.workspace_id,
            )
            .values(
                input_snapshot_json=self._redacted_payload(item),
                output_json=self._redacted_payload(item),
                output_text="[redacted by retention policy]",
            )
        )
        return await self._mark_mutation_result(item, int(result.rowcount or 0))

    async def _redact_chart_screenshot_run(
        self, item: DataRetentionRunItem
    ) -> DataRetentionRunItem:
        run = await self.session.get(ChartScreenshotRun, item.target_id)
        if run is None or run.workspace_id != item.workspace_id:
            return await self._skip_item(item, "target record was not found")
        parser_metadata = dict(run.parser_metadata_json)
        if "ocr" in parser_metadata:
            parser_metadata["ocr"] = self._redacted_payload(item)
        run.extracted_payload_json = self._redacted_payload(item)
        run.parser_metadata_json = parser_metadata
        return await self._mark_mutation_result(item, 1)

    async def _mark_mutation_result(
        self,
        item: DataRetentionRunItem,
        affected_rows: int,
    ) -> DataRetentionRunItem:
        if affected_rows == 0:
            return await self._skip_item(item, "target record was not found")
        item.status = DataRetentionRunItemStatus.APPLIED.value
        item.metadata_json = {
            **item.metadata_json,
            "appliedAt": utc_now().isoformat(),
            "affectedRows": affected_rows,
        }
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def _skip_item(self, item: DataRetentionRunItem, reason: str) -> DataRetentionRunItem:
        item.status = DataRetentionRunItemStatus.SKIPPED.value
        item.metadata_json = {
            **item.metadata_json,
            "skippedAt": utc_now().isoformat(),
            "skipReason": reason,
        }
        await self.session.flush()
        await self.session.refresh(item)
        return item

    def _redacted_payload(self, item: DataRetentionRunItem) -> dict[str, object]:
        return {
            "redacted": True,
            "redactedBy": "data_retention",
            "retentionRunId": str(item.retention_run_id),
            "retentionRunItemId": str(item.id),
        }
