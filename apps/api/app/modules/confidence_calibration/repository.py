from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.confidence_calibration.models import (
    ConfidenceCalibrationBin,
    ConfidenceCalibrationRun,
)
from app.modules.outcomes.models import SignalOutcome
from app.modules.signals.models import Signal


@dataclass(frozen=True)
class CalibrationOutcomeRow:
    signal_id: UUID
    horizon_minutes: int
    bias: str
    classification_status: str
    evaluation_status: str
    outcome_label: str
    confidence_score: Decimal


class ConfidenceCalibrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: ConfidenceCalibrationRun) -> ConfidenceCalibrationRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: ConfidenceCalibrationRun) -> ConfidenceCalibrationRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> ConfidenceCalibrationRun | None:
        return await self.session.get(ConfidenceCalibrationRun, run_id)

    async def list_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> list[ConfidenceCalibrationRun]:
        statement: Select[tuple[ConfidenceCalibrationRun]] = (
            select(ConfidenceCalibrationRun)
            .where(ConfidenceCalibrationRun.workspace_id == workspace_id)
            .order_by(ConfidenceCalibrationRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(ConfidenceCalibrationRun.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_bins(
        self,
        bins: list[ConfidenceCalibrationBin],
    ) -> list[ConfidenceCalibrationBin]:
        self.session.add_all(bins)
        await self.session.flush()
        for calibration_bin in bins:
            await self.session.refresh(calibration_bin)
        return bins

    async def list_bins(
        self,
        calibration_run_id: UUID,
        limit: int,
        offset: int,
        horizon_minutes: int | None = None,
        calibration_label: str | None = None,
    ) -> list[ConfidenceCalibrationBin]:
        statement: Select[tuple[ConfidenceCalibrationBin]] = (
            select(ConfidenceCalibrationBin)
            .where(ConfidenceCalibrationBin.calibration_run_id == calibration_run_id)
            .order_by(
                ConfidenceCalibrationBin.horizon_minutes.asc(),
                ConfidenceCalibrationBin.bin_min.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if horizon_minutes is not None:
            statement = statement.where(ConfidenceCalibrationBin.horizon_minutes == horizon_minutes)
        if calibration_label is not None:
            statement = statement.where(ConfidenceCalibrationBin.calibration_label == calibration_label)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_outcome_rows(
        self,
        workspace_id: UUID,
        horizons_minutes: list[int],
        limit: int,
        strategy_profile_key: str | None = None,
        pattern_type: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        bias: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[CalibrationOutcomeRow]:
        statement = (
            select(
                Signal.id,
                SignalOutcome.horizon_minutes,
                SignalOutcome.bias,
                SignalOutcome.classification_status,
                SignalOutcome.evaluation_status,
                SignalOutcome.outcome_label,
                Signal.confidence_score,
            )
            .join(SignalOutcome, SignalOutcome.signal_id == Signal.id)
            .where(
                Signal.workspace_id == workspace_id,
                SignalOutcome.workspace_id == workspace_id,
                SignalOutcome.horizon_minutes.in_(horizons_minutes),
            )
            .order_by(SignalOutcome.reference_time.desc(), SignalOutcome.created_at.desc())
            .limit(limit)
        )
        if strategy_profile_key is not None:
            statement = statement.where(SignalOutcome.strategy_profile_key == strategy_profile_key)
        if pattern_type is not None:
            statement = statement.where(SignalOutcome.pattern_type == pattern_type)
        if symbol_id is not None:
            statement = statement.where(SignalOutcome.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(SignalOutcome.timeframe == timeframe)
        if bias is not None:
            statement = statement.where(SignalOutcome.bias == bias)
        if start_time is not None:
            statement = statement.where(SignalOutcome.reference_time >= start_time)
        if end_time is not None:
            statement = statement.where(SignalOutcome.reference_time <= end_time)
        result = await self.session.execute(statement)
        return [
            CalibrationOutcomeRow(
                signal_id=row[0],
                horizon_minutes=row[1],
                bias=row[2],
                classification_status=row[3],
                evaluation_status=row[4],
                outcome_label=row[5],
                confidence_score=row[6],
            )
            for row in result.all()
        ]
