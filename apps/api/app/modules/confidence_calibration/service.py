from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.confidence_calibration.calculator import (
    CalibrationOutcome,
    ConfidenceCalibrationBinResult,
    ConfidenceCalibrationCalculator,
    ConfidenceCalibrationThresholds,
    bin_config_json,
    parse_bin_config,
)
from app.modules.confidence_calibration.models import (
    ConfidenceCalibrationBin,
    ConfidenceCalibrationRun,
    ConfidenceCalibrationRunStatus,
)
from app.modules.confidence_calibration.repository import (
    CalibrationOutcomeRow,
    ConfidenceCalibrationRepository,
)
from app.modules.confidence_calibration.schemas import ConfidenceCalibrationRunRequest
from app.modules.signals.models import SignalBias, SignalClassificationStatus


class ConfidenceCalibrationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ConfidenceCalibrationRepository(session)
        self.calculator = ConfidenceCalibrationCalculator()

    async def run_calibration(
        self,
        payload: ConfidenceCalibrationRunRequest,
    ) -> ConfidenceCalibrationRun:
        minimum_sample_size = (
            payload.minimum_sample_size or self.settings.confidence_calibration_minimum_sample_size
        )
        bin_definitions = parse_bin_config(
            payload.bin_config or self.settings.confidence_calibration_default_bins
        )
        run = await self.repository.create_run(
            ConfidenceCalibrationRun(
                workspace_id=payload.workspace_id,
                status=ConfidenceCalibrationRunStatus.PENDING.value,
                calibration_version=self.settings.confidence_calibration_version,
                filters_json=payload.filters.model_dump(mode="json"),
                horizons_json=payload.horizons_minutes,
                bin_config_json=bin_config_json(bin_definitions),
                minimum_sample_size=minimum_sample_size,
                summary="Confidence calibration pending.",
            )
        )
        try:
            rows = await self.repository.list_outcome_rows(
                workspace_id=payload.workspace_id,
                horizons_minutes=payload.horizons_minutes,
                strategy_profile_key=payload.filters.strategy_profile_key,
                pattern_type=payload.filters.pattern_type,
                symbol_id=payload.filters.symbol_id,
                timeframe=payload.filters.timeframe,
                bias=payload.filters.bias,
                start_time=payload.filters.start_time,
                end_time=payload.filters.end_time,
                limit=payload.filters.limit,
            )
            outcomes = [calibration_outcome_from_row(row) for row in rows]
            results = self.calculator.calculate_bins(
                outcomes=outcomes,
                horizons_minutes=payload.horizons_minutes,
                bin_definitions=bin_definitions,
                minimum_sample_size=minimum_sample_size,
                thresholds=self.thresholds,
            )
            bin_models = [
                calibration_bin_model(
                    workspace_id=payload.workspace_id,
                    calibration_run_id=run.id,
                    result=result,
                )
                for result in results
            ]
            await self.repository.create_bins(bin_models)
            directional_rows = [row for row in rows if is_directional_calibration_row(row)]
            run.evaluated_signal_count = len({row.signal_id for row in directional_rows})
            run.evaluated_outcome_count = len(directional_rows)
            run.bin_count = len(bin_models)
            run.summary = calibration_summary(results)
            run.status = run_status(results, minimum_sample_size)
            await self.repository.update_run(run)
            await self.session.commit()
            return run
        except Exception as error:
            run.status = ConfidenceCalibrationRunStatus.FAILED.value
            run.error_message = str(error)
            run.summary = "Confidence calibration failed."
            await self.repository.update_run(run)
            await self.session.commit()
            raise

    async def get_run(self, run_id: UUID) -> ConfidenceCalibrationRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(
                404,
                "confidence_calibration_run_not_found",
                "Confidence calibration run not found",
            )
        return run

    async def list_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> list[ConfidenceCalibrationRun]:
        return await self.repository.list_runs(
            workspace_id=workspace_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def list_bins(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
        horizon_minutes: int | None = None,
        calibration_label: str | None = None,
    ) -> list[ConfidenceCalibrationBin]:
        await self.get_run(run_id)
        return await self.repository.list_bins(
            calibration_run_id=run_id,
            horizon_minutes=horizon_minutes,
            calibration_label=calibration_label,
            limit=limit,
            offset=offset,
        )

    @property
    def thresholds(self) -> ConfidenceCalibrationThresholds:
        return ConfidenceCalibrationThresholds(
            overconfident_threshold=self.settings.confidence_calibration_overconfident_threshold,
            underconfident_threshold=self.settings.confidence_calibration_underconfident_threshold,
        )


def calibration_outcome_from_row(row: CalibrationOutcomeRow) -> CalibrationOutcome:
    return CalibrationOutcome(
        signal_id=row.signal_id,
        horizon_minutes=row.horizon_minutes,
        bias=row.bias,
        classification_status=row.classification_status,
        evaluation_status=row.evaluation_status,
        outcome_label=row.outcome_label,
        confidence_score=row.confidence_score,
    )


def is_directional_calibration_row(row: CalibrationOutcomeRow) -> bool:
    return row.classification_status == SignalClassificationStatus.SIGNAL.value and row.bias in {
        SignalBias.BULLISH.value,
        SignalBias.BEARISH.value,
    }


def calibration_bin_model(
    workspace_id: UUID,
    calibration_run_id: UUID,
    result: ConfidenceCalibrationBinResult,
) -> ConfidenceCalibrationBin:
    return ConfidenceCalibrationBin(
        workspace_id=workspace_id,
        calibration_run_id=calibration_run_id,
        horizon_minutes=result.horizon_minutes,
        bin_label=result.bin_label,
        bin_min=result.bin_min,
        bin_max=result.bin_max,
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
        calibration_label=result.calibration_label.value,
        metadata_json=result.metadata_json,
    )


def calibration_summary(results: list[ConfidenceCalibrationBinResult]) -> str:
    if not results:
        return "No confidence calibration bins were produced."
    label_counts: dict[str, int] = {}
    for result in results:
        label_counts[result.calibration_label.value] = (
            label_counts.get(result.calibration_label.value, 0) + 1
        )
    parts = [f"{label}={count}" for label, count in sorted(label_counts.items())]
    return "Confidence calibration completed with " + ", ".join(parts) + "."


def run_status(
    results: list[ConfidenceCalibrationBinResult],
    minimum_sample_size: int,
) -> str:
    if any(result.evaluated_count < minimum_sample_size for result in results):
        return ConfidenceCalibrationRunStatus.COMPLETED_WITH_WARNINGS.value
    return ConfidenceCalibrationRunStatus.COMPLETED.value
