from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.data_quality.models import (
    DataQualityFinding,
    DataQualityFindingSeverity,
    DataQualityLabel,
    DataQualityRun,
    DataQualityRunStatus,
    DataQualityScopeType,
)
from app.modules.data_quality.repository import DataQualityRepository
from app.modules.data_quality.schemas import DataQualityCandleRangeRequest


class DataQualityService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = DataQualityRepository(session)

    async def run_candle_range(self, request: DataQualityCandleRangeRequest) -> DataQualityRun:
        candle_count, partial_count, average_quality = await self.repository.summarize_candles(
            workspace_id=request.workspace_id,
            symbol_id=request.symbol_id,
            source_id=request.source_id,
            timeframe=request.timeframe,
            start_time=request.start_time,
            end_time=request.end_time,
        )
        score = Decimal(str(average_quality or 0)).quantize(Decimal("0.0001"))
        findings = build_findings(request.workspace_id, candle_count, partial_count, score, self.settings)
        run = await self.repository.create_run(
            DataQualityRun(
                workspace_id=request.workspace_id,
                scope_type=DataQualityScopeType.CANDLE_RANGE.value,
                status=(
                    DataQualityRunStatus.COMPLETED_WITH_WARNINGS.value
                    if findings
                    else DataQualityRunStatus.COMPLETED.value
                ),
                quality_version=self.settings.data_quality_version,
                symbol_id=request.symbol_id,
                source_id=request.source_id,
                timeframe=request.timeframe,
                start_time=request.start_time,
                end_time=request.end_time,
                candle_count=candle_count,
                finding_count=len(findings),
                quality_score=score,
                quality_label=quality_label(score, candle_count, self.settings).value,
                summary_json={
                    "dataQualityLabel": quality_label(score, candle_count, self.settings).value,
                    "partialCandleCount": partial_count,
                },
            ),
            findings,
        )
        await self.session.commit()
        return run

    async def run_source(self, workspace_id: UUID, source_id: UUID) -> DataQualityRun:
        candle_count, partial_count, average_quality = await self.repository.summarize_candles(
            workspace_id=workspace_id,
            source_id=source_id,
        )
        score = Decimal(str(average_quality or 0)).quantize(Decimal("0.0001"))
        findings = build_findings(workspace_id, candle_count, partial_count, score, self.settings)
        run = await self.repository.create_run(
            DataQualityRun(
                workspace_id=workspace_id,
                scope_type=DataQualityScopeType.DATA_SOURCE.value,
                status=DataQualityRunStatus.COMPLETED_WITH_WARNINGS.value if findings else DataQualityRunStatus.COMPLETED.value,
                quality_version=self.settings.data_quality_version,
                source_id=source_id,
                candle_count=candle_count,
                finding_count=len(findings),
                quality_score=score,
                quality_label=quality_label(score, candle_count, self.settings).value,
                summary_json={"dataQualityLabel": quality_label(score, candle_count, self.settings).value},
            ),
            findings,
        )
        await self.session.commit()
        return run

    async def run_live_subscription(self, workspace_id: UUID, subscription_id: UUID) -> DataQualityRun:
        run = await self.repository.create_run(
            DataQualityRun(
                workspace_id=workspace_id,
                live_subscription_id=subscription_id,
                scope_type=DataQualityScopeType.LIVE_SUBSCRIPTION.value,
                status=DataQualityRunStatus.COMPLETED.value,
                quality_version=self.settings.data_quality_version,
                candle_count=0,
                finding_count=0,
                quality_score=Decimal("1.0000"),
                quality_label=DataQualityLabel.STRONG.value,
                summary_json={"dataQualityLabel": DataQualityLabel.STRONG.value},
            ),
            [],
        )
        await self.session.commit()
        return run

    async def get_run(self, run_id: UUID) -> DataQualityRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "data_quality_run_not_found", "Data quality run not found")
        return run

    async def list_findings(self, run_id: UUID, limit: int, offset: int) -> list[DataQualityFinding]:
        await self.get_run(run_id)
        return await self.repository.list_findings(run_id, limit, offset)


def quality_label(score: Decimal, candle_count: int, settings: Settings) -> DataQualityLabel:
    if candle_count == 0:
        return DataQualityLabel.INSUFFICIENT_DATA
    if score >= settings.data_quality_strong_threshold:
        return DataQualityLabel.STRONG
    if score >= settings.data_quality_acceptable_threshold:
        return DataQualityLabel.ACCEPTABLE
    if score >= settings.data_quality_degraded_threshold:
        return DataQualityLabel.DEGRADED
    return DataQualityLabel.POOR


def build_findings(
    workspace_id: UUID,
    candle_count: int,
    partial_count: int,
    score: Decimal,
    settings: Settings,
) -> list[DataQualityFinding]:
    findings: list[DataQualityFinding] = []
    if candle_count == 0:
        findings.append(
            DataQualityFinding(
                workspace_id=workspace_id,
                data_quality_run_id=workspace_id,
                finding_type="insufficient_candles",
                severity=DataQualityFindingSeverity.HIGH.value,
                message="No candles were available for this data quality scope.",
                metadata_json={},
            )
        )
    if partial_count > 0:
        findings.append(
            DataQualityFinding(
                workspace_id=workspace_id,
                data_quality_run_id=workspace_id,
                finding_type="partial_candles_present",
                severity=DataQualityFindingSeverity.MEDIUM.value,
                message="Partial candles were present in the inspected scope.",
                metadata_json={"partialCandleCount": partial_count},
            )
        )
    if candle_count > 0 and score < settings.data_quality_acceptable_threshold:
        findings.append(
            DataQualityFinding(
                workspace_id=workspace_id,
                data_quality_run_id=workspace_id,
                finding_type="quality_score_below_acceptable",
                severity=DataQualityFindingSeverity.MEDIUM.value,
                message="Average candle quality was below the acceptable threshold.",
                metadata_json={"qualityScore": str(score)},
            )
        )
    return findings
