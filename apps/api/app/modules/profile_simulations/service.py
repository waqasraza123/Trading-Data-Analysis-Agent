from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.outcomes.models import SignalOutcome
from app.modules.profile_simulations.models import (
    StrategyProfileSimulationDecisionChangeType,
    StrategyProfileSimulationResult,
    StrategyProfileSimulationRun,
    StrategyProfileSimulationRunStatus,
)
from app.modules.profile_simulations.repository import ProfileSimulationRepository
from app.modules.profile_simulations.schemas import (
    ProfileSimulationRunRequest,
    ProfileSimulationSummary,
)
from app.modules.profile_simulations.simulator import (
    StrategyProfileSandboxSimulator,
    json_safe_value,
)
from app.modules.signals.models import SignalClassificationStatus
from app.modules.signals.service import SignalClassificationService
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.strategy_profiles.repository import StrategyProfileRepository


class ProfileSimulationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ProfileSimulationRepository(session)
        self.strategy_profile_repository = StrategyProfileRepository(session)
        self.classifier = SignalClassificationService(session)
        self.simulator = StrategyProfileSandboxSimulator(self.classifier)

    async def run_simulation(
        self,
        request: ProfileSimulationRunRequest,
    ) -> StrategyProfileSimulationRun:
        profile = await self.get_base_profile(
            key=request.base_strategy_profile_key,
            version=request.base_strategy_profile_version,
        )
        run = await self.repository.create_run(
            StrategyProfileSimulationRun(
                workspace_id=request.workspace_id,
                base_strategy_profile_key=profile.key,
                base_strategy_profile_version=profile.version,
                status=StrategyProfileSimulationRunStatus.PENDING.value,
                simulation_version=self.settings.profile_simulation_version,
                proposed_config_json=json_safe_mapping(request.proposed_config.model_dump()),
                filters_json=json_safe_mapping(
                    {
                        "workspaceId": str(request.workspace_id),
                        **request.filters.model_dump(),
                    }
                ),
                horizons_json=request.horizons_minutes,
                summary={},
            )
        )
        await self.session.commit()
        try:
            results = await self.build_results(run, profile, request)
            await self.repository.create_results(results)
            self.complete_run(run, results)
            await self.repository.update_run(run)
            await self.session.commit()
            return run
        except Exception as error:
            await self.session.rollback()
            failure_run = await self.repository.get_run(run.id)
            if failure_run is not None:
                failure_run.status = StrategyProfileSimulationRunStatus.FAILED.value
                failure_run.error_message = str(error)
                await self.repository.update_run(failure_run)
                await self.session.commit()
                return failure_run
            raise

    async def get_simulation_run(self, run_id: UUID) -> StrategyProfileSimulationRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "profile_simulation_run_not_found", "Simulation run not found")
        return run

    async def list_simulation_results(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[StrategyProfileSimulationResult]:
        await self.get_simulation_run(run_id)
        return await self.repository.list_results(run_id=run_id, limit=limit, offset=offset)

    async def summarize_simulation(self, run_id: UUID) -> ProfileSimulationSummary:
        run = await self.get_simulation_run(run_id)
        results = await self.repository.list_results(run_id=run_id, limit=5000, offset=0)
        decision_counts = Counter(result.decision_change_type for result in results)
        outcome_counts = Counter(
            result.outcome_label for result in results if result.outcome_label is not None
        )
        return ProfileSimulationSummary(
            run_id=run.id,
            sampled_signal_count=run.sampled_signal_count,
            included_count=run.included_count,
            excluded_count=run.excluded_count,
            changed_decision_count=run.changed_decision_count,
            outcome_labels=dict(outcome_counts),
            decision_changes=dict(decision_counts),
        )

    async def get_base_profile(self, key: str, version: str | None) -> StrategyProfile:
        profile = (
            await self.strategy_profile_repository.get_by_key_version(key, version)
            if version is not None
            else await self.strategy_profile_repository.get_by_key(key)
        )
        if profile is None:
            raise AppError(404, "strategy_profile_not_found", "Strategy profile not found")
        return profile

    async def build_results(
        self,
        run: StrategyProfileSimulationRun,
        profile: StrategyProfile,
        request: ProfileSimulationRunRequest,
    ) -> list[StrategyProfileSimulationResult]:
        effective_strategy_profile_key = (
            request.filters.strategy_profile_key or request.base_strategy_profile_key
        )
        signals = await self.repository.list_historical_signals(
            workspace_id=request.workspace_id,
            strategy_profile_key=effective_strategy_profile_key,
            symbol_id=request.filters.symbol_id,
            timeframe=request.filters.timeframe,
            pattern_type=request.filters.pattern_type,
            start_time=request.filters.start_time,
            end_time=request.filters.end_time,
            limit=min(request.filters.max_signals, self.settings.profile_simulation_max_signals),
        )
        results: list[StrategyProfileSimulationResult] = []
        for signal in signals:
            candidates = await self.repository.list_candidates(signal.analysis_run_id)
            feature_snapshot = await self.repository.get_feature_snapshot(signal.analysis_run_id)
            indicator_snapshot = await self.repository.get_indicator_snapshot(
                signal.analysis_run_id
            )
            outcomes = await self.repository.list_outcomes(signal.id, request.horizons_minutes)
            decision = self.simulator.simulate_signal(
                signal=signal,
                base_profile=profile,
                proposed_config=request.proposed_config,
                candidates=candidates,
                feature_snapshot=feature_snapshot,
                indicator_snapshot=indicator_snapshot,
                outcomes=outcomes,
            )
            primary_outcome = select_primary_outcome(outcomes, request.horizons_minutes)
            results.append(
                StrategyProfileSimulationResult(
                    workspace_id=signal.workspace_id,
                    simulation_run_id=run.id,
                    signal_id=signal.id,
                    analysis_run_id=signal.analysis_run_id,
                    symbol_id=signal.symbol_id,
                    timeframe=signal.timeframe,
                    original_classification_status=signal.classification_status,
                    original_bias=signal.bias,
                    original_pattern_type=signal.pattern_type,
                    original_confidence_score=signal.confidence_score,
                    simulated_classification_status=decision.classification_status,
                    simulated_bias=decision.bias,
                    simulated_pattern_type=decision.pattern_type,
                    simulated_confidence_score=decision.confidence_score,
                    decision_change_type=decision.decision_change_type.value,
                    outcome_label=primary_outcome.outcome_label if primary_outcome else None,
                    horizon_minutes=primary_outcome.horizon_minutes if primary_outcome else None,
                    reason_json=decision.reason_json,
                )
            )
        return results

    def complete_run(
        self,
        run: StrategyProfileSimulationRun,
        results: list[StrategyProfileSimulationResult],
    ) -> None:
        sampled_signal_count = len(results)
        included_count = sum(
            1
            for result in results
            if result.simulated_classification_status == SignalClassificationStatus.SIGNAL.value
        )
        excluded_count = sampled_signal_count - included_count
        changed_decision_count = sum(
            1
            for result in results
            if result.decision_change_type
            not in {
                StrategyProfileSimulationDecisionChangeType.UNCHANGED.value,
                StrategyProfileSimulationDecisionChangeType.NO_CANDIDATE.value,
            }
        )
        decision_counts = Counter(result.decision_change_type for result in results)
        outcome_counts = Counter(
            result.outcome_label for result in results if result.outcome_label is not None
        )
        no_candidate_count = decision_counts.get(
            StrategyProfileSimulationDecisionChangeType.NO_CANDIDATE.value,
            0,
        )
        run.sampled_signal_count = sampled_signal_count
        run.included_count = included_count
        run.excluded_count = excluded_count
        run.changed_decision_count = changed_decision_count
        run.status = (
            StrategyProfileSimulationRunStatus.COMPLETED_WITH_WARNINGS.value
            if no_candidate_count > 0
            else StrategyProfileSimulationRunStatus.COMPLETED.value
        )
        run.summary = {
            "decisionChanges": dict(decision_counts),
            "outcomeLabels": dict(outcome_counts),
            "includedHistoricalCases": included_count,
            "excludedHistoricalCases": excluded_count,
            "calibrationReview": {
                "reviewSuggested": changed_decision_count > 0,
                "changedDecisionCount": changed_decision_count,
                "noCandidateCount": no_candidate_count,
            },
        }


def select_primary_outcome(
    outcomes: list[SignalOutcome],
    horizons_minutes: list[int],
) -> SignalOutcome | None:
    for horizon in horizons_minutes:
        for outcome in outcomes:
            if outcome.horizon_minutes == horizon:
                return outcome
    return outcomes[0] if outcomes else None


def json_safe_mapping(values: dict[str, Any]) -> dict[str, object]:
    return {str(key): json_safe_value(value) for key, value in values.items() if value is not None}
