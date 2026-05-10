from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.outcomes.models import SignalOutcome
from app.modules.pattern_attribution.calculator import (
    AttributionThresholds,
    CandidateAttributionObservation,
    PatternAttributionAggregate,
    PatternAttributionCalculator,
    candidate_behavior,
    outcome_values_for_observation,
)
from app.modules.pattern_attribution.models import (
    PatternAttributionLabel,
    PatternAttributionResult,
    PatternAttributionRun,
    PatternAttributionRunStatus,
)
from app.modules.pattern_attribution.repository import (
    CandidateSignalRow,
    PatternAttributionRepository,
)
from app.modules.pattern_attribution.schemas import PatternAttributionRunRequest


class PatternAttributionService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = PatternAttributionRepository(session)
        self.calculator = PatternAttributionCalculator()

    async def run_attribution(
        self,
        payload: PatternAttributionRunRequest,
    ) -> PatternAttributionRun:
        minimum_sample_size = (
            payload.minimum_sample_size or self.settings.pattern_attribution_minimum_sample_size
        )
        run = await self.repository.create_run(
            PatternAttributionRun(
                workspace_id=payload.workspace_id,
                status=PatternAttributionRunStatus.PENDING.value,
                attribution_version=self.settings.pattern_attribution_version,
                filters_json=payload.filters.model_dump(mode="json"),
                horizons_json=payload.horizons_minutes,
                minimum_sample_size=minimum_sample_size,
                summary="Pattern attribution run is pending.",
            )
        )
        try:
            rows = await self.repository.list_candidate_signal_rows(
                workspace_id=payload.workspace_id,
                filters=payload.filters,
            )
            signal_ids = [row.signal.id for row in rows if row.signal is not None]
            outcomes_by_signal_horizon = await self.repository.list_outcomes_by_signal_ids(
                signal_ids=signal_ids,
                horizons_minutes=payload.horizons_minutes,
            )
            risk_note_codes = await self.repository.list_risk_note_codes_by_signal_ids(signal_ids)
            observations = build_observations(
                rows=rows,
                horizons_minutes=payload.horizons_minutes,
                outcomes_by_signal_horizon=outcomes_by_signal_horizon,
                risk_note_codes_by_signal_id=risk_note_codes,
            )
            aggregates = self.calculator.build_results(
                observations=observations,
                minimum_sample_size=minimum_sample_size,
                thresholds=self.thresholds,
            )
            await self.repository.create_results(
                [result_model(run.id, aggregate) for aggregate in aggregates]
            )
            run.evaluated_candidate_count = len({row.candidate.id for row in rows})
            run.evaluated_signal_count = len(
                {row.signal.id for row in rows if row.signal is not None}
            )
            run.result_count = len(aggregates)
            run.status = completed_status(aggregates)
            run.summary = run_summary(
                candidate_count=run.evaluated_candidate_count,
                signal_count=run.evaluated_signal_count,
                result_count=run.result_count,
            )
            await self.repository.update_run(run)
            await self.session.commit()
            return run
        except Exception as error:
            run.status = PatternAttributionRunStatus.FAILED.value
            run.error_message = str(error)
            run.summary = "Pattern attribution failed before diagnostics were completed."
            await self.repository.update_run(run)
            await self.session.commit()
            return run

    async def get_attribution_run(self, run_id: UUID) -> PatternAttributionRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(
                404,
                "pattern_attribution_run_not_found",
                "Pattern attribution run not found",
            )
        return run

    async def list_attribution_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> list[PatternAttributionRun]:
        return await self.repository.list_runs(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    async def list_attribution_results(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
        attribution_label: str | None = None,
        pattern_type: str | None = None,
    ) -> list[PatternAttributionResult]:
        await self.get_attribution_run(run_id)
        return await self.repository.list_results(
            run_id=run_id,
            limit=limit,
            offset=offset,
            attribution_label=attribution_label,
            pattern_type=pattern_type,
        )

    @property
    def thresholds(self) -> AttributionThresholds:
        return AttributionThresholds(
            high_rejection_rate=self.settings.pattern_attribution_high_rejection_rate,
            high_reversal_rate=self.settings.pattern_attribution_high_reversal_rate,
        )


def build_observations(
    rows: list[CandidateSignalRow],
    horizons_minutes: list[int],
    outcomes_by_signal_horizon: dict[tuple[UUID, int], SignalOutcome],
    risk_note_codes_by_signal_id: dict[UUID, set[str]],
) -> list[CandidateAttributionObservation]:
    observations: list[CandidateAttributionObservation] = []
    for row in rows:
        signal = row.signal
        selected_candidate_id = signal.selected_pattern_candidate_id if signal is not None else None
        signal_id = signal.id if signal is not None else None
        behavior = candidate_behavior(
            candidate_id=row.candidate.id,
            pattern_type=row.candidate.pattern_type,
            signal_selected_candidate_id=selected_candidate_id,
            signal_classification_status=(
                signal.classification_status if signal is not None else None
            ),
            signal_no_signal_reason=signal.no_signal_reason if signal is not None else None,
            signal_risk_note_codes=(
                risk_note_codes_by_signal_id.get(signal.id, set()) if signal is not None else set()
            ),
        )
        for horizon_minutes in horizons_minutes:
            outcome = (
                outcomes_by_signal_horizon.get((signal.id, horizon_minutes))
                if signal is not None
                else None
            )
            outcome_label, evaluation_status = outcome_values_for_observation(
                behavior=behavior,
                outcome_label=outcome.outcome_label if outcome is not None else None,
                evaluation_status=outcome.evaluation_status if outcome is not None else None,
            )
            observations.append(
                CandidateAttributionObservation(
                    workspace_id=row.candidate.workspace_id,
                    candidate_id=row.candidate.id,
                    signal_id=signal_id,
                    pattern_type=row.candidate.pattern_type,
                    strategy_profile_key=(
                        signal.strategy_profile_key if signal is not None else None
                    ),
                    symbol_id=row.candidate.symbol_id,
                    timeframe=(
                        signal.timeframe if signal is not None else row.analysis_run.timeframe
                    ),
                    horizon_minutes=horizon_minutes,
                    strength_score=row.candidate.strength_score,
                    selected_confidence=(
                        signal.confidence_score
                        if signal is not None and behavior in {"selected", "blocked"}
                        else None
                    ),
                    behavior=behavior,
                    outcome_label=outcome_label,
                    evaluation_status=evaluation_status,
                    missing_outcome=(
                        signal is not None
                        and behavior in {"selected", "blocked"}
                        and outcome is None
                    ),
                )
            )
    return observations


def result_model(
    attribution_run_id: UUID,
    result: PatternAttributionAggregate,
) -> PatternAttributionResult:
    return PatternAttributionResult(
        workspace_id=result.workspace_id,
        attribution_run_id=attribution_run_id,
        pattern_type=result.pattern_type,
        strategy_profile_key=result.strategy_profile_key,
        symbol_id=result.symbol_id,
        timeframe=result.timeframe,
        horizon_minutes=result.horizon_minutes,
        candidate_count=result.candidate_count,
        selected_count=result.selected_count,
        rejected_count=result.rejected_count,
        blocked_count=result.blocked_count,
        average_strength_score=result.average_strength_score,
        average_selected_confidence=result.average_selected_confidence,
        continuation_count=result.continuation_count,
        partial_follow_through_count=result.partial_follow_through_count,
        no_follow_through_count=result.no_follow_through_count,
        reversal_count=result.reversal_count,
        insufficient_data_count=result.insufficient_data_count,
        continuation_rate=result.continuation_rate,
        reversal_rate=result.reversal_rate,
        no_follow_through_rate=result.no_follow_through_rate,
        attribution_label=result.attribution_label.value,
        diagnostic_summary=result.diagnostic_summary,
        metadata_json=result.metadata_json,
    )


def completed_status(aggregates: list[PatternAttributionAggregate]) -> str:
    if not aggregates:
        return PatternAttributionRunStatus.COMPLETED_WITH_WARNINGS.value
    warning_labels = {
        PatternAttributionLabel.LOW_SAMPLE,
        PatternAttributionLabel.INSUFFICIENT_DATA,
    }
    if any(aggregate.attribution_label in warning_labels for aggregate in aggregates):
        return PatternAttributionRunStatus.COMPLETED_WITH_WARNINGS.value
    return PatternAttributionRunStatus.COMPLETED.value


def run_summary(candidate_count: int, signal_count: int, result_count: int) -> str:
    if candidate_count == 0:
        return "No pattern candidates matched the bounded attribution filters."
    return (
        f"Evaluated {candidate_count} pattern candidates across {signal_count} final signals "
        f"and created {result_count} detector attribution diagnostics."
    )
