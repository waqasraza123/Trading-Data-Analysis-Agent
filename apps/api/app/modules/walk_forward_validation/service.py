from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.outcomes.models import OutcomeEvaluationStatus
from app.modules.walk_forward_validation.calculator import (
    WalkForwardComparisonResult,
    WalkForwardThresholds,
    WalkForwardValidationCalculator,
    WalkForwardWindowResult,
)
from app.modules.walk_forward_validation.models import (
    WalkForwardStabilityLabel,
    WalkForwardValidationComparison,
    WalkForwardValidationRun,
    WalkForwardValidationRunStatus,
    WalkForwardValidationWindow,
)
from app.modules.walk_forward_validation.repository import (
    WalkForwardOutcomeRow,
    WalkForwardValidationRepository,
)
from app.modules.walk_forward_validation.schemas import WalkForwardValidationRunRequest


class WalkForwardValidationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = WalkForwardValidationRepository(session)
        self.calculator = WalkForwardValidationCalculator()

    async def run_validation(
        self,
        request: WalkForwardValidationRunRequest,
    ) -> WalkForwardValidationRun:
        window_days = request.window_days or self.settings.walk_forward_default_window_days
        minimum_sample_size = (
            request.minimum_sample_size or self.settings.walk_forward_minimum_sample_size
        )
        run = await self.repository.create_run(
            WalkForwardValidationRun(
                workspace_id=request.workspace_id,
                name=request.name,
                status=WalkForwardValidationRunStatus.PENDING.value,
                validation_version=self.settings.walk_forward_validation_version,
                filters_json=json_safe_mapping(request.filters.model_dump()),
                window_config_json={"windowDays": window_days},
                horizons_json=request.horizons_minutes,
                minimum_sample_size=minimum_sample_size,
                summary="Walk-forward validation pending.",
            )
        )
        try:
            resolved_start, resolved_end = await self.resolve_time_bounds(request)
            run.window_config_json = {
                "windowDays": window_days,
                "startTime": resolved_start.isoformat() if resolved_start is not None else None,
                "endTime": resolved_end.isoformat() if resolved_end is not None else None,
                "startTimeInferred": request.filters.start_time is None,
                "endTimeInferred": request.filters.end_time is None,
            }
            if resolved_start is None or resolved_end is None:
                run.status = WalkForwardValidationRunStatus.COMPLETED_WITH_WARNINGS.value
                run.summary = (
                    "No stored signal outcomes matched the walk-forward validation filters."
                )
                await self.repository.update_run(run)
                await self.session.commit()
                return run
            rows = await self.repository.list_outcome_rows(
                workspace_id=request.workspace_id,
                horizons_minutes=request.horizons_minutes,
                filters=request.filters,
                start_time=resolved_start,
                end_time=resolved_end,
            )
            thresholds = self.thresholds
            window_ranges = self.calculator.split_windows(
                start_time=resolved_start,
                end_time=resolved_end,
                window_days=window_days,
            )
            window_results = self.calculator.calculate_windows(
                workspace_id=request.workspace_id,
                rows=rows,
                windows=window_ranges,
                horizons_minutes=request.horizons_minutes,
                minimum_sample_size=minimum_sample_size,
                thresholds=thresholds,
            )
            comparison_results = self.calculator.compare_windows(
                workspace_id=request.workspace_id,
                window_results=window_results,
                horizons_minutes=request.horizons_minutes,
                thresholds=thresholds,
            )
            await self.repository.create_windows(
                [
                    window_model(
                        validation_run_id=run.id,
                        result=result,
                    )
                    for result in window_results
                ]
            )
            await self.repository.create_comparisons(
                [
                    comparison_model(
                        validation_run_id=run.id,
                        result=result,
                    )
                    for result in comparison_results
                ]
            )
            evaluated_rows = evaluated_source_rows(rows)
            run.window_count = len(window_ranges)
            run.evaluated_signal_count = len({row.signal_id for row in evaluated_rows})
            run.evaluated_outcome_count = len(evaluated_rows)
            run.summary = validation_summary(
                window_count=run.window_count,
                evaluated_signal_count=run.evaluated_signal_count,
                evaluated_outcome_count=run.evaluated_outcome_count,
                window_results=window_results,
                comparison_results=comparison_results,
            )
            run.status = validation_status(window_results, comparison_results)
            await self.repository.update_run(run)
            await self.session.commit()
            return run
        except Exception as error:
            run.status = WalkForwardValidationRunStatus.FAILED.value
            run.error_message = str(error)
            run.summary = "Walk-forward validation failed."
            await self.repository.update_run(run)
            await self.session.commit()
            return run

    async def resolve_time_bounds(
        self,
        request: WalkForwardValidationRunRequest,
    ) -> tuple[datetime | None, datetime | None]:
        bounds = await self.repository.source_bounds(
            workspace_id=request.workspace_id,
            horizons_minutes=request.horizons_minutes,
            filters=request.filters,
        )
        start_time = request.filters.start_time or bounds.start_time
        end_time = request.filters.end_time or bounds.end_time
        return start_time, end_time

    async def get_run(self, run_id: UUID) -> WalkForwardValidationRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(
                404,
                "walk_forward_validation_run_not_found",
                "Walk-forward validation run not found",
            )
        return run

    async def list_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> list[WalkForwardValidationRun]:
        return await self.repository.list_runs(
            workspace_id=workspace_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def list_windows(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
        horizon_minutes: int | None = None,
        stability_label: str | None = None,
    ) -> list[WalkForwardValidationWindow]:
        await self.get_run(run_id)
        return await self.repository.list_windows(
            validation_run_id=run_id,
            horizon_minutes=horizon_minutes,
            stability_label=stability_label,
            limit=limit,
            offset=offset,
        )

    async def list_comparisons(
        self,
        run_id: UUID,
    ) -> list[WalkForwardValidationComparison]:
        await self.get_run(run_id)
        return await self.repository.list_comparisons(validation_run_id=run_id)

    @property
    def thresholds(self) -> WalkForwardThresholds:
        return WalkForwardThresholds(
            degradation_threshold=self.settings.walk_forward_degradation_threshold,
            improvement_threshold=self.settings.walk_forward_improvement_threshold,
        )


def window_model(
    validation_run_id: UUID,
    result: WalkForwardWindowResult,
) -> WalkForwardValidationWindow:
    return WalkForwardValidationWindow(
        workspace_id=result.workspace_id,
        validation_run_id=validation_run_id,
        window_index=result.window_index,
        window_start=result.window_start,
        window_end=result.window_end,
        horizon_minutes=result.horizon_minutes,
        sample_size=result.sample_size,
        evaluated_count=result.evaluated_count,
        continuation_count=result.continuation_count,
        partial_follow_through_count=result.partial_follow_through_count,
        no_follow_through_count=result.no_follow_through_count,
        reversal_count=result.reversal_count,
        insufficient_data_count=result.insufficient_data_count,
        continuation_rate=result.continuation_rate,
        reversal_rate=result.reversal_rate,
        no_follow_through_rate=result.no_follow_through_rate,
        average_confidence_score=result.average_confidence_score,
        confidence_alignment_score=result.confidence_alignment_score,
        stability_label=result.stability_label.value,
        summary=result.summary,
        metadata_json=result.metadata_json,
    )


def comparison_model(
    validation_run_id: UUID,
    result: WalkForwardComparisonResult,
) -> WalkForwardValidationComparison:
    return WalkForwardValidationComparison(
        workspace_id=result.workspace_id,
        validation_run_id=validation_run_id,
        horizon_minutes=result.horizon_minutes,
        compared_window_count=result.compared_window_count,
        stability_score=result.stability_score,
        degradation_detected=result.degradation_detected,
        improvement_detected=result.improvement_detected,
        summary=result.summary,
        metadata_json=result.metadata_json,
    )


def evaluated_source_rows(rows: list[WalkForwardOutcomeRow]) -> list[WalkForwardOutcomeRow]:
    return [row for row in rows if row.evaluation_status == OutcomeEvaluationStatus.EVALUATED.value]


def validation_status(
    window_results: list[WalkForwardWindowResult],
    comparison_results: list[WalkForwardComparisonResult],
) -> str:
    if not window_results:
        return WalkForwardValidationRunStatus.COMPLETED_WITH_WARNINGS.value
    warning_labels = {
        WalkForwardStabilityLabel.LOW_SAMPLE,
        WalkForwardStabilityLabel.INSUFFICIENT_DATA,
    }
    if any(result.stability_label in warning_labels for result in window_results):
        return WalkForwardValidationRunStatus.COMPLETED_WITH_WARNINGS.value
    if any(result.compared_window_count < 2 for result in comparison_results):
        return WalkForwardValidationRunStatus.COMPLETED_WITH_WARNINGS.value
    return WalkForwardValidationRunStatus.COMPLETED.value


def validation_summary(
    window_count: int,
    evaluated_signal_count: int,
    evaluated_outcome_count: int,
    window_results: list[WalkForwardWindowResult],
    comparison_results: list[WalkForwardComparisonResult],
) -> str:
    if evaluated_outcome_count == 0:
        return "No evaluated stored outcomes were available for walk-forward validation."
    low_sample_count = sum(
        1
        for result in window_results
        if result.stability_label == WalkForwardStabilityLabel.LOW_SAMPLE
    )
    insufficient_count = sum(
        1
        for result in window_results
        if result.stability_label == WalkForwardStabilityLabel.INSUFFICIENT_DATA
    )
    degradation_count = sum(1 for result in comparison_results if result.degradation_detected)
    improvement_count = sum(1 for result in comparison_results if result.improvement_detected)
    return (
        f"Validated {evaluated_outcome_count} evaluated stored outcomes from "
        f"{evaluated_signal_count} signals across {window_count} walk-forward windows. "
        f"Low-sample windows: {low_sample_count}. Insufficient-data windows: {insufficient_count}. "
        f"Degradation comparisons: {degradation_count}. "
        f"Improvement comparisons: {improvement_count}."
    )


def json_safe_mapping(values: dict[str, Any]) -> dict[str, object]:
    return {str(key): json_safe_value(value) for key, value in values.items() if value is not None}


def json_safe_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return json_safe_mapping(value)
    if isinstance(value, list):
        return [json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe_value(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
