from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.cohort_drift.calculator import (
    CohortDriftCalculationResult,
    CohortDriftCalculator,
    CohortDriftThresholds,
)
from app.modules.cohort_drift.models import (
    CohortDriftLabel,
    CohortDriftResult,
    CohortDriftRun,
    CohortDriftRunStatus,
)
from app.modules.cohort_drift.repository import CohortDriftRepository
from app.modules.cohort_drift.schemas import (
    CohortDriftRecentResultsFilters,
    CohortDriftRunRequest,
)


@dataclass(frozen=True)
class ResolvedCohortDriftWindow:
    start_time: datetime
    end_time: datetime


class CohortDriftService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = CohortDriftRepository(session)
        self.calculator = CohortDriftCalculator()

    async def run_drift_detection(self, payload: CohortDriftRunRequest) -> CohortDriftRun:
        minimum_sample_size = (
            payload.minimum_sample_size or self.settings.cohort_drift_minimum_sample_size
        )
        baseline_window, comparison_window = self.resolve_windows(payload)
        run = await self.repository.create_run(
            CohortDriftRun(
                workspace_id=payload.workspace_id,
                status=CohortDriftRunStatus.PENDING.value,
                drift_version=self.settings.cohort_drift_version,
                filters_json=payload.filters.model_dump(mode="json", exclude_none=True),
                baseline_window_json=window_json(baseline_window),
                comparison_window_json=window_json(comparison_window),
                cohort_dimensions_json=payload.cohort_dimensions,
                horizons_json=payload.horizons_minutes,
                minimum_sample_size=minimum_sample_size,
                summary="Cohort drift detection pending.",
            )
        )
        try:
            baseline_rows = await self.repository.list_outcome_rows(
                workspace_id=payload.workspace_id,
                horizons_minutes=payload.horizons_minutes,
                filters=payload.filters,
                start_time=baseline_window.start_time,
                end_time=baseline_window.end_time,
            )
            comparison_rows = await self.repository.list_outcome_rows(
                workspace_id=payload.workspace_id,
                horizons_minutes=payload.horizons_minutes,
                filters=payload.filters,
                start_time=comparison_window.start_time,
                end_time=comparison_window.end_time,
            )
            results = self.calculator.calculate_results(
                workspace_id=payload.workspace_id,
                baseline_rows=baseline_rows,
                comparison_rows=comparison_rows,
                dimensions=payload.cohort_dimensions,
                horizons_minutes=payload.horizons_minutes,
                minimum_sample_size=minimum_sample_size,
                thresholds=self.thresholds,
            )
            await self.repository.create_results(
                [
                    drift_result_model(
                        drift_run_id=run.id,
                        result=result,
                    )
                    for result in results
                ]
            )
            run.cohort_count = len(results)
            run.drift_detected_count = drift_detected_count(results)
            run.summary = drift_run_summary(
                baseline_outcome_count=len(baseline_rows),
                comparison_outcome_count=len(comparison_rows),
                result_count=len(results),
                drift_count=run.drift_detected_count,
                low_sample_count=label_count(results, CohortDriftLabel.LOW_SAMPLE),
                insufficient_count=label_count(results, CohortDriftLabel.INSUFFICIENT_DATA),
            )
            run.status = drift_run_status(results)
            await self.repository.update_run(run)
            await self.session.commit()
            return run
        except Exception as error:
            run.status = CohortDriftRunStatus.FAILED.value
            run.error_message = str(error)
            run.summary = "Cohort drift detection failed."
            await self.repository.update_run(run)
            await self.session.commit()
            return run

    def resolve_windows(
        self,
        payload: CohortDriftRunRequest,
    ) -> tuple[ResolvedCohortDriftWindow, ResolvedCohortDriftWindow]:
        now = utc_now()
        default_comparison_end = now
        default_comparison_start = default_comparison_end - timedelta(
            days=self.settings.cohort_drift_default_comparison_days
        )
        comparison_start = (
            payload.comparison_window.start_time
            if payload.comparison_window is not None
            and payload.comparison_window.start_time is not None
            else default_comparison_start
        )
        comparison_end = (
            payload.comparison_window.end_time
            if payload.comparison_window is not None
            and payload.comparison_window.end_time is not None
            else default_comparison_end
        )
        default_baseline_end = comparison_start
        default_baseline_start = default_baseline_end - timedelta(
            days=self.settings.cohort_drift_default_baseline_days
        )
        baseline_start = (
            payload.baseline_window.start_time
            if payload.baseline_window is not None
            and payload.baseline_window.start_time is not None
            else default_baseline_start
        )
        baseline_end = (
            payload.baseline_window.end_time
            if payload.baseline_window is not None
            and payload.baseline_window.end_time is not None
            else default_baseline_end
        )
        if baseline_start >= baseline_end:
            msg = "Resolved baseline window must have start_time before end_time"
            raise ValueError(msg)
        if comparison_start >= comparison_end:
            msg = "Resolved comparison window must have start_time before end_time"
            raise ValueError(msg)
        if baseline_end > comparison_start:
            msg = "Resolved baseline window must end before or at comparison window start"
            raise ValueError(msg)
        return (
            ResolvedCohortDriftWindow(start_time=baseline_start, end_time=baseline_end),
            ResolvedCohortDriftWindow(start_time=comparison_start, end_time=comparison_end),
        )

    async def get_drift_run(self, run_id: UUID) -> CohortDriftRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "cohort_drift_run_not_found", "Cohort drift run not found")
        return run

    async def list_drift_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> list[CohortDriftRun]:
        return await self.repository.list_runs(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    async def list_drift_results(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
        drift_label: str | None = None,
        severity: str | None = None,
        horizon_minutes: int | None = None,
        cohort_key: str | None = None,
    ) -> list[CohortDriftResult]:
        await self.get_drift_run(run_id)
        return await self.repository.list_results(
            drift_run_id=run_id,
            limit=limit,
            offset=offset,
            drift_label=drift_label,
            severity=severity,
            horizon_minutes=horizon_minutes,
            cohort_key=cohort_key,
        )

    async def list_recent_drift_results(
        self,
        workspace_id: UUID,
        filters: CohortDriftRecentResultsFilters,
    ) -> list[CohortDriftResult]:
        return await self.repository.list_recent_results(
            workspace_id=workspace_id,
            limit=filters.limit,
            offset=filters.offset,
            drift_label=filters.drift_label.value if filters.drift_label is not None else None,
            severity=filters.severity.value if filters.severity is not None else None,
            horizon_minutes=filters.horizon_minutes,
            cohort_key=filters.cohort_key,
        )

    @property
    def thresholds(self) -> CohortDriftThresholds:
        return CohortDriftThresholds(
            mild_threshold=self.settings.cohort_drift_mild_threshold,
            moderate_threshold=self.settings.cohort_drift_moderate_threshold,
            severe_threshold=self.settings.cohort_drift_severe_threshold,
        )


def drift_result_model(
    drift_run_id: UUID,
    result: CohortDriftCalculationResult,
) -> CohortDriftResult:
    return CohortDriftResult(
        workspace_id=result.workspace_id,
        drift_run_id=drift_run_id,
        cohort_key=result.cohort_key,
        cohort_dimensions_json=result.cohort_dimensions_json,
        horizon_minutes=result.horizon_minutes,
        baseline_sample_size=result.baseline_sample_size,
        comparison_sample_size=result.comparison_sample_size,
        baseline_continuation_rate=result.baseline_continuation_rate,
        comparison_continuation_rate=result.comparison_continuation_rate,
        continuation_rate_delta=result.continuation_rate_delta,
        baseline_reversal_rate=result.baseline_reversal_rate,
        comparison_reversal_rate=result.comparison_reversal_rate,
        reversal_rate_delta=result.reversal_rate_delta,
        baseline_no_follow_through_rate=result.baseline_no_follow_through_rate,
        comparison_no_follow_through_rate=result.comparison_no_follow_through_rate,
        no_follow_through_delta=result.no_follow_through_delta,
        baseline_confidence_alignment=result.baseline_confidence_alignment,
        comparison_confidence_alignment=result.comparison_confidence_alignment,
        confidence_alignment_delta=result.confidence_alignment_delta,
        drift_score=result.drift_score,
        drift_label=result.drift_label.value,
        severity=result.severity.value,
        summary=result.summary,
        metadata_json=result.metadata_json,
    )


def window_json(window: ResolvedCohortDriftWindow) -> dict[str, object]:
    return {
        "startTime": window.start_time.isoformat(),
        "endTime": window.end_time.isoformat(),
    }


def drift_detected_count(results: list[CohortDriftCalculationResult]) -> int:
    return sum(
        1
        for result in results
        if result.drift_label
        in {
            CohortDriftLabel.MILD_DRIFT,
            CohortDriftLabel.MODERATE_DRIFT,
            CohortDriftLabel.SEVERE_DRIFT,
        }
    )


def label_count(
    results: list[CohortDriftCalculationResult],
    label: CohortDriftLabel,
) -> int:
    return sum(1 for result in results if result.drift_label == label)


def drift_run_status(results: list[CohortDriftCalculationResult]) -> str:
    if not results:
        return CohortDriftRunStatus.COMPLETED_WITH_WARNINGS.value
    warning_labels = {CohortDriftLabel.LOW_SAMPLE, CohortDriftLabel.INSUFFICIENT_DATA}
    if any(result.drift_label in warning_labels for result in results):
        return CohortDriftRunStatus.COMPLETED_WITH_WARNINGS.value
    return CohortDriftRunStatus.COMPLETED.value


def drift_run_summary(
    baseline_outcome_count: int,
    comparison_outcome_count: int,
    result_count: int,
    drift_count: int,
    low_sample_count: int,
    insufficient_count: int,
) -> str:
    if result_count == 0:
        return "No stored signal outcome cohorts matched the baseline and recent-window filters."
    return (
        f"Compared {baseline_outcome_count} baseline stored outcomes with "
        f"{comparison_outcome_count} recent-window stored outcomes across {result_count} cohorts. "
        f"Drift detected: {drift_count}. Low-sample cohorts: {low_sample_count}. "
        f"Insufficient-data cohorts: {insufficient_count}."
    )
