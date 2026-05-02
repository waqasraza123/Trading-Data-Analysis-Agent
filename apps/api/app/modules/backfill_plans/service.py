from hashlib import sha256
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.backfill_plans.models import (
    BackfillPlanStatus,
    IntelligenceBackfillItem,
    IntelligenceBackfillPlan,
)
from app.modules.backfill_plans.planner import BackfillPlanPlanner, PreparedBackfillPlan
from app.modules.backfill_plans.repository import BackfillPlanRepository
from app.modules.backfill_plans.schemas import (
    BackfillItemListQuery,
    BackfillPlanCreate,
    BackfillPlanFilters,
    BackfillPlanListQuery,
)


class BackfillPlanService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = BackfillPlanRepository(session)
        self.planner = BackfillPlanPlanner(session, self.settings)

    async def create_backfill_plan(self, payload: BackfillPlanCreate) -> IntelligenceBackfillPlan:
        prepared_plan = await self.planner.prepare_plan(payload)
        status = (
            BackfillPlanStatus.READY
            if prepared_plan.planned_count > 0
            else BackfillPlanStatus.DRAFT
        )
        plan = await self.repository.create_plan(
            IntelligenceBackfillPlan(
                workspace_id=payload.workspace_id,
                plan_type=payload.plan_type,
                status=status,
                plan_version=self.settings.backfill_plan_version,
                filters_json=prepared_plan.filters_json,
                target_module=prepared_plan.target_module,
                target_operation=prepared_plan.target_operation,
                dry_run=payload.dry_run,
                eligible_count=prepared_plan.eligible_count,
                planned_count=prepared_plan.planned_count,
                skipped_count=prepared_plan.skipped_count,
                blocked_count=prepared_plan.blocked_count,
                summary=prepared_plan.summary,
                metadata_json=prepared_plan.metadata_json,
            )
        )
        await self.repository.create_items(self.build_items(plan, prepared_plan))
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def get_backfill_plan(self, plan_id: UUID) -> IntelligenceBackfillPlan:
        plan = await self.repository.get_plan(plan_id)
        if plan is None:
            raise AppError(404, "backfill_plan_not_found", "Backfill plan not found")
        return plan

    async def list_backfill_plans(
        self,
        query: BackfillPlanListQuery,
    ) -> list[IntelligenceBackfillPlan]:
        return await self.repository.list_plans(
            workspace_id=query.workspace_id,
            plan_type=query.plan_type,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )

    async def list_backfill_items(
        self,
        plan_id: UUID,
        query: BackfillItemListQuery,
    ) -> list[IntelligenceBackfillItem]:
        await self.get_backfill_plan(plan_id)
        return await self.repository.list_items(
            plan_id=plan_id,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )

    async def cancel_backfill_plan(self, plan_id: UUID) -> IntelligenceBackfillPlan:
        plan = await self.get_backfill_plan(plan_id)
        if plan.status in {
            BackfillPlanStatus.COMPLETED,
            BackfillPlanStatus.CANCELLED,
            BackfillPlanStatus.FAILED,
        }:
            return plan
        cancelled = await self.repository.cancel_plan(plan)
        await self.session.commit()
        return cancelled

    async def prepare_missing_outcomes_plan(self, payload: BackfillPlanCreate) -> PreparedBackfillPlan:
        filters = self.normalized_filters(payload)
        return await self.planner.prepare_missing_outcomes_plan(
            payload,
            filters,
            self.planner.resolve_contract(payload),
        )

    async def prepare_missing_context_plan(self, payload: BackfillPlanCreate) -> PreparedBackfillPlan:
        filters = self.normalized_filters(payload)
        return await self.planner.prepare_missing_context_plan(
            payload,
            filters,
            self.planner.resolve_contract(payload),
        )

    async def prepare_stale_artifacts_plan(self, payload: BackfillPlanCreate) -> PreparedBackfillPlan:
        filters = self.normalized_filters(payload)
        return await self.planner.prepare_stale_artifacts_plan(
            payload,
            filters,
            self.planner.resolve_contract(payload),
        )

    async def prepare_module_backfill_plan(self, payload: BackfillPlanCreate) -> PreparedBackfillPlan:
        filters = self.normalized_filters(payload)
        return await self.planner.prepare_module_backfill_plan(
            payload,
            filters,
            self.planner.resolve_contract(payload),
        )

    def normalized_filters(self, payload: BackfillPlanCreate) -> BackfillPlanFilters:
        limit = self.planner.resolve_limit(payload.filters.limit)
        return payload.filters.model_copy(update={"limit": limit})

    def build_items(
        self,
        plan: IntelligenceBackfillPlan,
        prepared_plan: PreparedBackfillPlan,
    ) -> list[IntelligenceBackfillItem]:
        return [
            IntelligenceBackfillItem(
                workspace_id=plan.workspace_id,
                backfill_plan_id=plan.id,
                target_type=candidate.target_type,
                target_id=candidate.target_id,
                target_operation=candidate.target_operation,
                status=candidate.status,
                priority=candidate.priority,
                idempotency_key=self.idempotency_key(plan, candidate.target_type, candidate.target_id),
                input_json=candidate.input_json,
                skip_reason=candidate.skip_reason,
                block_reason=candidate.block_reason,
            )
            for candidate in prepared_plan.candidates
        ]

    def idempotency_key(self, plan: IntelligenceBackfillPlan, target_type: str, target_id: UUID) -> str:
        raw_key = f"{plan.id}:{plan.target_operation}:{target_type}:{target_id}"
        return sha256(raw_key.encode("utf-8")).hexdigest()
