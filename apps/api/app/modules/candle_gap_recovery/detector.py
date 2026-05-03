from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.modules.candles.models import Candle
from app.modules.candles.timeframes import (
    Timeframe,
    expected_timestamps,
    normalize_timestamp,
    timeframe_duration,
)


@dataclass(frozen=True)
class CandleGapRange:
    gap_start_time: datetime
    gap_end_time: datetime
    expected_candle_count: int


@dataclass(frozen=True)
class CandleGapDetectionResult:
    gaps: list[CandleGapRange]
    expected_candle_count: int
    available_final_candle_count: int
    missing_candle_count: int
    truncated_gap_count: int
    metadata_json: dict[str, object] = field(default_factory=dict)


class CandleGapRecoveryDetector:
    def __init__(self, max_gaps: int) -> None:
        self.max_gaps = max_gaps

    def detect_missing_final_candles(
        self,
        *,
        candles: list[Candle],
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
    ) -> CandleGapDetectionResult:
        normalized_start = normalize_timestamp(start_time)
        normalized_end = normalize_timestamp(end_time)
        expected = expected_timestamps(
            start_time=normalized_start,
            end_time=normalized_end,
            timeframe=timeframe,
        )
        expected_set = set(expected)
        final_timestamps = {
            normalize_timestamp(candle.timestamp)
            for candle in candles
            if candle.is_final and normalize_timestamp(candle.timestamp) in expected_set
        }
        missing_timestamps = sorted(expected_set - final_timestamps)
        grouped_gaps = group_missing_timestamps(missing_timestamps, timeframe)
        retained_gaps = grouped_gaps[: self.max_gaps]
        truncated_gap_count = max(len(grouped_gaps) - len(retained_gaps), 0)
        return CandleGapDetectionResult(
            gaps=retained_gaps,
            expected_candle_count=len(expected),
            available_final_candle_count=len(final_timestamps),
            missing_candle_count=len(missing_timestamps),
            truncated_gap_count=truncated_gap_count,
            metadata_json={
                "workspaceId": str(workspace_id),
                "symbolId": str(symbol_id),
                "sourceId": str(source_id) if source_id is not None else None,
                "timeframe": timeframe.value,
                "startTime": normalized_start.isoformat(),
                "endTime": normalized_end.isoformat(),
                "expectedCandleCount": len(expected),
                "availableFinalCandleCount": len(final_timestamps),
                "missingCandleCount": len(missing_timestamps),
                "groupedGapCount": len(grouped_gaps),
                "retainedGapCount": len(retained_gaps),
                "truncatedGapCount": truncated_gap_count,
                "finalCandlesOnly": True,
            },
        )


def group_missing_timestamps(
    missing_timestamps: list[datetime],
    timeframe: Timeframe,
) -> list[CandleGapRange]:
    if not missing_timestamps:
        return []
    duration = timeframe_duration(timeframe)
    gaps: list[CandleGapRange] = []
    gap_start = missing_timestamps[0]
    gap_end = missing_timestamps[0]
    count = 1
    for timestamp in missing_timestamps[1:]:
        if timestamp == gap_end + duration:
            gap_end = timestamp
            count += 1
            continue
        gaps.append(
            CandleGapRange(
                gap_start_time=gap_start,
                gap_end_time=gap_end,
                expected_candle_count=count,
            )
        )
        gap_start = timestamp
        gap_end = timestamp
        count = 1
    gaps.append(
        CandleGapRange(
            gap_start_time=gap_start,
            gap_end_time=gap_end,
            expected_candle_count=count,
        )
    )
    return gaps
