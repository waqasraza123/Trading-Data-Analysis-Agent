from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Select, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisMode, AnalysisRun, AnalysisRunStatus
from app.modules.backfill_plans.models import (
    BackfillItemPriority,
    BackfillItemStatus,
    BackfillItemTargetType,
    BackfillPlanType,
)
from app.modules.backfill_plans.schemas import BackfillPlanCreate, BackfillPlanFilters
from app.modules.outcomes.models import SignalOutcome
from app.modules.signals.models import Signal


class BackfillModuleAvailability(StrEnum):
    AVAILABLE = "available"
    MODULE_UNAVAILABLE = "module_unavailable"
    ARTIFACT_GRAPH_UNAVAILABLE = "artifact_graph_unavailable"
    EXECUTION_REGISTRY_UNAVAILABLE = "execution_registry_unavailable"


@dataclass(frozen=True)
class BackfillOperationContract:
    operation: str
    target_module: str
    target_type: BackfillItemTargetType
    availability: BackfillModuleAvailability


@dataclass(frozen=True)
class PlannedBackfillCandidate:
    target_type: BackfillItemTargetType
    target_id: UUID
    target_operation: str
    status: BackfillItemStatus
    priority: BackfillItemPriority
    input_json: dict[str, object]
    skip_reason: str | None = None
    block_reason: str | None = None


@dataclass(frozen=True)
class PreparedBackfillPlan:
    target_module: str
    target_operation: str
    filters_json: dict[str, object]
    candidates: list[PlannedBackfillCandidate]
    summary: str
    metadata_json: dict[str, object]

    @property
    def eligible_count(self) -> int:
        return len(self.candidates)

    @property
    def planned_count(self) -> int:
        return sum(
            1 for candidate in self.candidates if candidate.status == BackfillItemStatus.PLANNED
        )

    @property
    def skipped_count(self) -> int:
        return sum(
            1 for candidate in self.candidates if candidate.status == BackfillItemStatus.SKIPPED
        )

    @property
    def blocked_count(self) -> int:
        return sum(
            1 for candidate in self.candidates if candidate.status == BackfillItemStatus.BLOCKED
        )


OPERATION_CONTRACTS: dict[str, BackfillOperationContract] = {
    "outcomes.evaluate": BackfillOperationContract(
        operation="outcomes.evaluate",
        target_module="outcomes",
        target_type=BackfillItemTargetType.SIGNAL,
        availability=BackfillModuleAvailability.AVAILABLE,
    ),
    "market_regime.generate": BackfillOperationContract(
        operation="market_regime.generate",
        target_module="market_regimes",
        target_type=BackfillItemTargetType.ANALYSIS_RUN,
        availability=BackfillModuleAvailability.MODULE_UNAVAILABLE,
    ),
    "market_session.generate": BackfillOperationContract(
        operation="market_session.generate",
        target_module="market_sessions",
        target_type=BackfillItemTargetType.ANALYSIS_RUN,
        availability=BackfillModuleAvailability.MODULE_UNAVAILABLE,
    ),
    "advanced_features.generate": BackfillOperationContract(
        operation="advanced_features.generate",
        target_module="advanced_features",
        target_type=BackfillItemTargetType.ANALYSIS_RUN,
        availability=BackfillModuleAvailability.MODULE_UNAVAILABLE,
    ),
    "historical_case_vector.generate": BackfillOperationContract(
        operation="historical_case_vector.generate",
        target_module="historical_cases",
        target_type=BackfillItemTargetType.SIGNAL,
        availability=BackfillModuleAvailability.MODULE_UNAVAILABLE,
    ),
    "reproducibility_manifest.generate": BackfillOperationContract(
        operation="reproducibility_manifest.generate",
        target_module="rule_manifests",
        target_type=BackfillItemTargetType.ANALYSIS_RUN,
        availability=BackfillModuleAvailability.AVAILABLE,
    ),
    "decision_readiness.assess": BackfillOperationContract(
        operation="decision_readiness.assess",
        target_module="decision_readiness",
        target_type=BackfillItemTargetType.ANALYSIS_RUN,
        availability=BackfillModuleAvailability.MODULE_UNAVAILABLE,
    ),
    "intelligence_quality.run": BackfillOperationContract(
        operation="intelligence_quality.run",
        target_module="intelligence_quality",
        target_type=BackfillItemTargetType.ANALYSIS_RUN,
        availability=BackfillModuleAvailability.MODULE_UNAVAILABLE,
    ),
    "data_quality.run": BackfillOperationContract(
        operation="data_quality.run",
        target_module="data_quality",
        target_type=BackfillItemTargetType.WORKSPACE,
        availability=BackfillModuleAvailability.AVAILABLE,
    ),
    "confidence_calibration.run": BackfillOperationContract(
        operation="confidence_calibration.run",
        target_module="confidence_calibration",
        target_type=BackfillItemTargetType.WORKSPACE,
        availability=BackfillModuleAvailability.AVAILABLE,
    ),
}


DEFAULT_OPERATION_BY_PLAN_TYPE: dict[BackfillPlanType, str] = {
    BackfillPlanType.MISSING_ARTIFACTS: "outcomes.evaluate",
    BackfillPlanType.STALE_ARTIFACTS: "reproducibility_manifest.generate",
    BackfillPlanType.MODULE_BACKFILL: "outcomes.evaluate",
    BackfillPlanType.OUTCOME_BACKFILL: "outcomes.evaluate",
    BackfillPlanType.CONTEXT_BACKFILL: "market_session.generate",
    BackfillPlanType.QUALITY_BACKFILL: "data_quality.run",
    BackfillPlanType.DATASET_BACKFILL: "data_quality.run",
}


class BackfillPlanPlanner:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    async def prepare_plan(self, payload: BackfillPlanCreate) -> PreparedBackfillPlan:
        contract = self.resolve_contract(payload)
        limit = self.resolve_limit(payload.filters.limit)
        filters = payload.filters.model_copy(update={"limit": limit})
        if payload.plan_type == BackfillPlanType.OUTCOME_BACKFILL:
            return await self.prepare_missing_outcomes_plan(payload, filters, contract)
        if payload.plan_type == BackfillPlanType.CONTEXT_BACKFILL:
            return await self.prepare_missing_context_plan(payload, filters, contract)
        if payload.plan_type == BackfillPlanType.STALE_ARTIFACTS:
            return await self.prepare_stale_artifacts_plan(payload, filters, contract)
        if payload.plan_type in {
            BackfillPlanType.MODULE_BACKFILL,
            BackfillPlanType.MISSING_ARTIFACTS,
            BackfillPlanType.QUALITY_BACKFILL,
            BackfillPlanType.DATASET_BACKFILL,
        }:
            return await self.prepare_module_backfill_plan(payload, filters, contract)
        raise AppError(422, "unsupported_backfill_plan_type", "Unsupported backfill plan type")

    async def prepare_missing_outcomes_plan(
        self,
        payload: BackfillPlanCreate,
        filters: BackfillPlanFilters,
        contract: BackfillOperationContract,
    ) -> PreparedBackfillPlan:
        horizons = filters.horizons_minutes or self.settings.outcome_default_horizons_minutes
        signals = await self.list_signals_missing_outcomes(payload.workspace_id, filters, horizons)
        candidates = [
            self.build_candidate(
                target_type=BackfillItemTargetType.SIGNAL,
                target_id=signal.id,
                target_operation=contract.operation,
                input_json={
                    "workspaceId": str(signal.workspace_id),
                    "signalId": str(signal.id),
                    "analysisRunId": str(signal.analysis_run_id),
                    "symbolId": str(signal.symbol_id),
                    "timeframe": signal.timeframe,
                    "horizonsMinutes": horizons,
                    "dryRun": payload.dry_run,
                },
                availability=contract.availability,
            )
            for signal in signals
        ]
        return self.build_prepared_plan(payload, filters, contract, candidates)

    async def prepare_missing_context_plan(
        self,
        payload: BackfillPlanCreate,
        filters: BackfillPlanFilters,
        contract: BackfillOperationContract,
    ) -> PreparedBackfillPlan:
        analysis_runs = await self.list_completed_analysis_runs(payload.workspace_id, filters)
        candidates = [
            self.build_candidate(
                target_type=BackfillItemTargetType.ANALYSIS_RUN,
                target_id=analysis_run.id,
                target_operation=contract.operation,
                input_json=self.analysis_run_input(analysis_run, payload.dry_run),
                availability=contract.availability,
            )
            for analysis_run in analysis_runs
        ]
        return self.build_prepared_plan(payload, filters, contract, candidates)

    async def prepare_stale_artifacts_plan(
        self,
        payload: BackfillPlanCreate,
        filters: BackfillPlanFilters,
        contract: BackfillOperationContract,
    ) -> PreparedBackfillPlan:
        candidate = PlannedBackfillCandidate(
            target_type=BackfillItemTargetType.WORKSPACE,
            target_id=payload.workspace_id,
            target_operation=contract.operation,
            status=BackfillItemStatus.BLOCKED,
            priority=BackfillItemPriority.NORMAL,
            input_json={
                "workspaceId": str(payload.workspace_id),
                "filters": filters.model_dump(mode="json", by_alias=True, exclude_none=True),
                "dryRun": payload.dry_run,
            },
            block_reason=BackfillModuleAvailability.ARTIFACT_GRAPH_UNAVAILABLE.value,
        )
        return self.build_prepared_plan(payload, filters, contract, [candidate])

    async def prepare_module_backfill_plan(
        self,
        payload: BackfillPlanCreate,
        filters: BackfillPlanFilters,
        contract: BackfillOperationContract,
    ) -> PreparedBackfillPlan:
        if contract.operation == "outcomes.evaluate":
            return await self.prepare_missing_outcomes_plan(payload, filters, contract)
        if contract.operation == "reproducibility_manifest.generate":
            analysis_runs = await self.list_analysis_runs_missing_reproducibility(
                payload.workspace_id, filters
            )
            candidates = [
                self.build_candidate(
                    target_type=BackfillItemTargetType.ANALYSIS_RUN,
                    target_id=analysis_run.id,
                    target_operation=contract.operation,
                    input_json=self.analysis_run_input(analysis_run, payload.dry_run),
                    availability=contract.availability,
                )
                for analysis_run in analysis_runs
            ]
            return self.build_prepared_plan(payload, filters, contract, candidates)
        if contract.target_type == BackfillItemTargetType.WORKSPACE:
            candidate = self.build_candidate(
                target_type=BackfillItemTargetType.WORKSPACE,
                target_id=payload.workspace_id,
                target_operation=contract.operation,
                input_json={
                    "workspaceId": str(payload.workspace_id),
                    "filters": filters.model_dump(mode="json", by_alias=True, exclude_none=True),
                    "dryRun": payload.dry_run,
                    "boundedBatchLimit": filters.limit,
                },
                availability=contract.availability,
            )
            return self.build_prepared_plan(payload, filters, contract, [candidate])
        if contract.target_type == BackfillItemTargetType.SIGNAL:
            signals = await self.list_signals(payload.workspace_id, filters)
            candidates = [
                self.build_candidate(
                    target_type=BackfillItemTargetType.SIGNAL,
                    target_id=signal.id,
                    target_operation=contract.operation,
                    input_json={
                        "workspaceId": str(signal.workspace_id),
                        "signalId": str(signal.id),
                        "analysisRunId": str(signal.analysis_run_id),
                        "symbolId": str(signal.symbol_id),
                        "timeframe": signal.timeframe,
                        "dryRun": payload.dry_run,
                    },
                    availability=contract.availability,
                )
                for signal in signals
            ]
            return self.build_prepared_plan(payload, filters, contract, candidates)
        analysis_runs = await self.list_completed_analysis_runs(payload.workspace_id, filters)
        candidates = [
            self.build_candidate(
                target_type=BackfillItemTargetType.ANALYSIS_RUN,
                target_id=analysis_run.id,
                target_operation=contract.operation,
                input_json=self.analysis_run_input(analysis_run, payload.dry_run),
                availability=contract.availability,
            )
            for analysis_run in analysis_runs
        ]
        return self.build_prepared_plan(payload, filters, contract, candidates)

    async def list_signals_missing_outcomes(
        self,
        workspace_id: UUID,
        filters: BackfillPlanFilters,
        horizons: Sequence[int],
    ) -> list[Signal]:
        limit = self.resolve_limit(filters.limit)
        statement = self.signal_statement(workspace_id, filters)
        missing_horizon_predicates = [
            ~exists(
                select(SignalOutcome.id).where(
                    SignalOutcome.signal_id == Signal.id,
                    SignalOutcome.horizon_minutes == horizon,
                    SignalOutcome.evaluation_version == self.settings.outcome_evaluation_version,
                )
            )
            for horizon in horizons
        ]
        statement = statement.where(or_(*missing_horizon_predicates)).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_signals(self, workspace_id: UUID, filters: BackfillPlanFilters) -> list[Signal]:
        limit = self.resolve_limit(filters.limit)
        result = await self.session.execute(
            self.signal_statement(workspace_id, filters).limit(limit)
        )
        return list(result.scalars().all())

    async def list_completed_analysis_runs(
        self,
        workspace_id: UUID,
        filters: BackfillPlanFilters,
    ) -> list[AnalysisRun]:
        limit = self.resolve_limit(filters.limit)
        result = await self.session.execute(
            self.analysis_run_statement(workspace_id, filters).limit(limit)
        )
        return list(result.scalars().all())

    async def list_analysis_runs_missing_reproducibility(
        self,
        workspace_id: UUID,
        filters: BackfillPlanFilters,
    ) -> list[AnalysisRun]:
        limit = self.resolve_limit(filters.limit)
        statement = self.analysis_run_statement(workspace_id, filters).where(
            or_(
                AnalysisRun.engine_snapshot_json.is_(None),
                AnalysisRun.rule_set_snapshot_json.is_(None),
            )
        )
        result = await self.session.execute(statement.limit(limit))
        return list(result.scalars().all())

    def signal_statement(
        self, workspace_id: UUID, filters: BackfillPlanFilters
    ) -> Select[tuple[Signal]]:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .join(AnalysisRun, AnalysisRun.id == Signal.analysis_run_id)
            .where(Signal.workspace_id == workspace_id)
            .order_by(Signal.created_at.asc(), Signal.id.asc())
        )
        if filters.symbol_id is not None:
            statement = statement.where(Signal.symbol_id == filters.symbol_id)
        if filters.timeframe is not None:
            statement = statement.where(Signal.timeframe == filters.timeframe)
        if filters.start_time is not None:
            statement = statement.where(AnalysisRun.end_time >= filters.start_time)
        if filters.end_time is not None:
            statement = statement.where(AnalysisRun.end_time <= filters.end_time)
        if not filters.include_replay:
            statement = statement.where(AnalysisRun.analysis_mode != AnalysisMode.REPLAY)
        return statement

    def analysis_run_statement(
        self,
        workspace_id: UUID,
        filters: BackfillPlanFilters,
    ) -> Select[tuple[AnalysisRun]]:
        statement: Select[tuple[AnalysisRun]] = (
            select(AnalysisRun)
            .where(
                AnalysisRun.workspace_id == workspace_id,
                AnalysisRun.status == AnalysisRunStatus.COMPLETED,
            )
            .order_by(AnalysisRun.created_at.asc(), AnalysisRun.id.asc())
        )
        if filters.symbol_id is not None:
            statement = statement.where(AnalysisRun.symbol_id == filters.symbol_id)
        if filters.timeframe is not None:
            statement = statement.where(AnalysisRun.timeframe == filters.timeframe)
        if filters.start_time is not None:
            statement = statement.where(AnalysisRun.end_time >= filters.start_time)
        if filters.end_time is not None:
            statement = statement.where(AnalysisRun.end_time <= filters.end_time)
        if not filters.include_replay:
            statement = statement.where(AnalysisRun.analysis_mode != AnalysisMode.REPLAY)
        return statement

    def build_prepared_plan(
        self,
        payload: BackfillPlanCreate,
        filters: BackfillPlanFilters,
        contract: BackfillOperationContract,
        candidates: list[PlannedBackfillCandidate],
    ) -> PreparedBackfillPlan:
        metadata_json: dict[str, object] = {
            "operationAvailability": contract.availability.value,
            "createExecutionRecordsRequested": payload.create_execution_records,
            "executionRegistryStatus": (
                BackfillModuleAvailability.EXECUTION_REGISTRY_UNAVAILABLE.value
            ),
            "sourceArtifactMutationAllowed": False,
            "externalProviderCallsAllowed": False,
            "automaticExecutionAllowed": False,
        }
        if payload.create_execution_records:
            metadata_json["executionRecordsCreated"] = 0
        summary = self.plan_summary(payload.plan_type, contract, candidates)
        return PreparedBackfillPlan(
            target_module=payload.target_module or contract.target_module,
            target_operation=contract.operation,
            filters_json=filters.model_dump(mode="json", by_alias=True, exclude_none=True),
            candidates=candidates,
            summary=summary,
            metadata_json=metadata_json,
        )

    def build_candidate(
        self,
        target_type: BackfillItemTargetType,
        target_id: UUID,
        target_operation: str,
        input_json: dict[str, object],
        availability: BackfillModuleAvailability,
    ) -> PlannedBackfillCandidate:
        if availability == BackfillModuleAvailability.AVAILABLE:
            return PlannedBackfillCandidate(
                target_type=target_type,
                target_id=target_id,
                target_operation=target_operation,
                status=BackfillItemStatus.PLANNED,
                priority=BackfillItemPriority.NORMAL,
                input_json=input_json,
            )
        return PlannedBackfillCandidate(
            target_type=target_type,
            target_id=target_id,
            target_operation=target_operation,
            status=BackfillItemStatus.BLOCKED,
            priority=BackfillItemPriority.NORMAL,
            input_json=input_json,
            block_reason=availability.value,
        )

    def resolve_contract(self, payload: BackfillPlanCreate) -> BackfillOperationContract:
        operation = payload.target_operation or DEFAULT_OPERATION_BY_PLAN_TYPE[payload.plan_type]
        contract = OPERATION_CONTRACTS.get(operation)
        if contract is None:
            raise AppError(
                422, "unsupported_backfill_operation", "Unsupported backfill target operation"
            )
        return contract

    def resolve_limit(self, requested_limit: int | None) -> int:
        limit = requested_limit or self.settings.backfill_plan_default_limit
        if limit > self.settings.backfill_plan_max_limit:
            raise AppError(
                422,
                "backfill_plan_limit_exceeded",
                "Backfill plan limit exceeds configured maximum",
            )
        return limit

    def analysis_run_input(self, analysis_run: AnalysisRun, dry_run: bool) -> dict[str, object]:
        return {
            "workspaceId": str(analysis_run.workspace_id),
            "analysisRunId": str(analysis_run.id),
            "symbolId": str(analysis_run.symbol_id),
            "sourceId": str(analysis_run.source_id) if analysis_run.source_id is not None else None,
            "timeframe": analysis_run.timeframe,
            "startTime": analysis_run.start_time.isoformat(),
            "endTime": analysis_run.end_time.isoformat(),
            "analysisMode": analysis_run.analysis_mode,
            "dryRun": dry_run,
        }

    def plan_summary(
        self,
        plan_type: BackfillPlanType,
        contract: BackfillOperationContract,
        candidates: list[PlannedBackfillCandidate],
    ) -> str:
        planned_count = sum(
            1 for candidate in candidates if candidate.status == BackfillItemStatus.PLANNED
        )
        blocked_count = sum(
            1 for candidate in candidates if candidate.status == BackfillItemStatus.BLOCKED
        )
        skipped_count = sum(
            1 for candidate in candidates if candidate.status == BackfillItemStatus.SKIPPED
        )
        return (
            f"{plan_type.value} prepared {len(candidates)} eligible artifact(s) for "
            f"{contract.operation}: {planned_count} planned, {blocked_count} blocked, "
            f"{skipped_count} skipped"
        )
