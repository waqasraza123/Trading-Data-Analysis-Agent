from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.candles.models import Candle
from app.modules.candles.timeframes import (
    Timeframe,
    expected_timestamps,
    normalize_timestamp,
    timeframe_duration,
    timestamp_aligns_with_timeframe,
)
from app.modules.data_quality.models import (
    DataQualityFindingType,
    DataQualityLabel,
    DataQualitySeverity,
)
from app.modules.live.models import LiveFeedSubscription

FINDING_PENALTIES: dict[DataQualitySeverity, Decimal] = {
    DataQualitySeverity.INFO: Decimal("0.01000"),
    DataQualitySeverity.LOW: Decimal("0.04000"),
    DataQualitySeverity.MEDIUM: Decimal("0.10000"),
    DataQualitySeverity.HIGH: Decimal("0.20000"),
    DataQualitySeverity.CRITICAL: Decimal("0.35000"),
}


@dataclass(frozen=True)
class QualityThresholds:
    strong: Decimal
    acceptable: Decimal
    degraded: Decimal


@dataclass(frozen=True)
class DetectedFinding:
    finding_type: DataQualityFindingType
    severity: DataQualitySeverity
    message: str
    symbol_id: UUID | None = None
    source_id: UUID | None = None
    live_subscription_id: UUID | None = None
    timeframe: str | None = None
    timestamp: datetime | None = None
    expected_value: str | None = None
    observed_value: str | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DetectionResult:
    findings: list[DetectedFinding]
    checked_candle_count: int
    expected_candle_count: int
    quality_score: Decimal
    quality_label: DataQualityLabel
    summary: str
    metadata_json: dict[str, object]


class DataQualityDetector:
    def __init__(
        self,
        *,
        thresholds: QualityThresholds,
        outlier_range_multiplier: Decimal,
        data_quality_version: str,
    ) -> None:
        self.thresholds = thresholds
        self.outlier_range_multiplier = outlier_range_multiplier
        self.data_quality_version = data_quality_version

    def detect_candle_range(
        self,
        *,
        candles: list[Candle],
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        expected_candle_count: int,
    ) -> DetectionResult:
        normalized_start = normalize_timestamp(start_time)
        normalized_end = normalize_timestamp(end_time)
        findings: list[DetectedFinding] = []
        expected = expected_timestamps(
            start_time=normalized_start,
            end_time=normalized_end,
            timeframe=timeframe,
        )
        expected_set = set(expected)
        final_candles = [candle for candle in candles if candle.is_final]
        final_timestamps = {normalize_timestamp(candle.timestamp) for candle in final_candles}
        missing_timestamps = sorted(expected_set - final_timestamps)
        for timestamp in missing_timestamps:
            findings.append(
                DetectedFinding(
                    finding_type=DataQualityFindingType.MISSING_CANDLES,
                    severity=DataQualitySeverity.MEDIUM,
                    symbol_id=symbol_id,
                    source_id=source_id,
                    timeframe=timeframe.value,
                    timestamp=timestamp,
                    message="Expected final candle is missing",
                    expected_value=timestamp.isoformat(),
                    observed_value=None,
                )
            )
        for candle in candles:
            if not timestamp_aligns_with_timeframe(candle.timestamp, timeframe):
                findings.append(
                    DetectedFinding(
                        finding_type=DataQualityFindingType.TIMESTAMP_MISALIGNMENT,
                        severity=DataQualitySeverity.MEDIUM,
                        symbol_id=symbol_id,
                        source_id=candle.source_id,
                        timeframe=timeframe.value,
                        timestamp=candle.timestamp,
                        message="Candle timestamp is not aligned with timeframe",
                        expected_value=timeframe.value,
                        observed_value=candle.timestamp.isoformat(),
                    )
                )
        findings.extend(
            self.detect_duplicate_and_conflicting_candles(
                candles=candles,
                symbol_id=symbol_id,
                requested_source_id=source_id,
                timeframe=timeframe,
            )
        )
        findings.extend(
            self.detect_price_quality_findings(
                candles=final_candles,
                symbol_id=symbol_id,
                requested_source_id=source_id,
                timeframe=timeframe,
            )
        )
        completeness = Decimal("1")
        if expected_set:
            completeness = Decimal(len(final_timestamps & expected_set)) / Decimal(
                len(expected_set)
            )
        if expected_set and completeness < self.thresholds.acceptable:
            findings.append(
                DetectedFinding(
                    finding_type=DataQualityFindingType.LOW_COMPLETENESS,
                    severity=(
                        DataQualitySeverity.HIGH
                        if completeness < self.thresholds.degraded
                        else DataQualitySeverity.MEDIUM
                    ),
                    symbol_id=symbol_id,
                    source_id=source_id,
                    timeframe=timeframe.value,
                    message="Final candle completeness is below the acceptable threshold",
                    expected_value=str(self.thresholds.acceptable),
                    observed_value=str(completeness.quantize(Decimal("0.00001"))),
                    metadata_json={
                        "expectedCandleCount": expected_candle_count,
                        "availableFinalCandleCount": len(final_timestamps & expected_set),
                    },
                )
            )
        return self.build_result(
            findings=findings,
            checked_candle_count=len(candles),
            expected_candle_count=expected_candle_count,
            summary_subject="Candle range quality check",
            extra_metadata={
                "workspaceId": str(workspace_id),
                "symbolId": str(symbol_id),
                "sourceId": str(source_id) if source_id is not None else None,
                "timeframe": timeframe.value,
                "startTime": normalized_start.isoformat(),
                "endTime": normalized_end.isoformat(),
                "completeness": str(completeness.quantize(Decimal("0.00001"))),
            },
        )

    def detect_live_subscription(
        self,
        *,
        subscription: LiveFeedSubscription,
        now: datetime,
        stale_after_seconds: int,
    ) -> DetectionResult:
        findings: list[DetectedFinding] = []
        normalized_now = normalize_timestamp(now)
        last_message_age = seconds_since(subscription.last_message_at, normalized_now)
        last_final_age = seconds_since(subscription.last_final_candle_at, normalized_now)
        if subscription.last_message_at is None or last_message_age > stale_after_seconds:
            findings.append(
                DetectedFinding(
                    finding_type=DataQualityFindingType.STALE_LIVE_FEED,
                    severity=DataQualitySeverity.HIGH,
                    symbol_id=subscription.symbol_id,
                    source_id=subscription.source_id,
                    live_subscription_id=subscription.id,
                    timeframe=subscription.timeframe,
                    message="Live subscription has not received a recent provider message",
                    expected_value=f"<={stale_after_seconds}s",
                    observed_value=(
                        "never" if last_message_age is None else f"{last_message_age}s"
                    ),
                    metadata_json={"stalenessBasis": "lastMessageAt"},
                )
            )
        if subscription.last_final_candle_at is None or last_final_age > stale_after_seconds:
            findings.append(
                DetectedFinding(
                    finding_type=DataQualityFindingType.STALE_LIVE_FEED,
                    severity=DataQualitySeverity.MEDIUM,
                    symbol_id=subscription.symbol_id,
                    source_id=subscription.source_id,
                    live_subscription_id=subscription.id,
                    timeframe=subscription.timeframe,
                    message="Live subscription has not produced a recent final candle",
                    expected_value=f"<={stale_after_seconds}s",
                    observed_value="never" if last_final_age is None else f"{last_final_age}s",
                    metadata_json={"stalenessBasis": "lastFinalCandleAt"},
                )
            )
        return self.build_result(
            findings=findings,
            checked_candle_count=0,
            expected_candle_count=0,
            summary_subject="Live subscription quality check",
            extra_metadata={
                "subscriptionId": str(subscription.id),
                "status": subscription.status,
                "provider": subscription.provider,
                "staleAfterSeconds": stale_after_seconds,
                "lastMessageAt": (
                    subscription.last_message_at.isoformat()
                    if subscription.last_message_at is not None
                    else None
                ),
                "lastFinalCandleAt": (
                    subscription.last_final_candle_at.isoformat()
                    if subscription.last_final_candle_at is not None
                    else None
                ),
            },
        )

    def detect_duplicate_and_conflicting_candles(
        self,
        *,
        candles: list[Candle],
        symbol_id: UUID,
        requested_source_id: UUID | None,
        timeframe: Timeframe,
    ) -> list[DetectedFinding]:
        findings: list[DetectedFinding] = []
        by_timestamp: dict[datetime, list[Candle]] = defaultdict(list)
        for candle in candles:
            by_timestamp[normalize_timestamp(candle.timestamp)].append(candle)
        for timestamp, timestamp_candles in by_timestamp.items():
            final_candles = [candle for candle in timestamp_candles if candle.is_final]
            partial_candles = [candle for candle in timestamp_candles if not candle.is_final]
            source_counts = Counter(candle.source_id for candle in timestamp_candles)
            duplicate_sources = [
                source_id for source_id, count in source_counts.items() if count > 1
            ]
            if len(timestamp_candles) > 1:
                findings.append(
                    DetectedFinding(
                        finding_type=DataQualityFindingType.DUPLICATE_CANDLES,
                        severity=DataQualitySeverity.LOW,
                        symbol_id=symbol_id,
                        source_id=requested_source_id,
                        timeframe=timeframe.value,
                        timestamp=timestamp,
                        message="Multiple candle rows exist for the same timestamp in this scope",
                        expected_value="1",
                        observed_value=str(len(timestamp_candles)),
                        metadata_json={
                            "sourceIds": sorted(
                                {str(candle.source_id) for candle in timestamp_candles}
                            ),
                            "duplicateSourceIds": [
                                str(source_id) for source_id in duplicate_sources
                            ],
                        },
                    )
                )
            if final_candles and partial_candles:
                findings.append(
                    DetectedFinding(
                        finding_type=DataQualityFindingType.PARTIAL_AFTER_FINAL,
                        severity=DataQualitySeverity.MEDIUM,
                        symbol_id=symbol_id,
                        source_id=requested_source_id,
                        timeframe=timeframe.value,
                        timestamp=timestamp,
                        message="Partial and final candles coexist for the same timestamp",
                        expected_value="final only",
                        observed_value="partial and final",
                    )
                )
            if len(final_candles) > 1 and final_values_conflict(final_candles):
                findings.append(
                    DetectedFinding(
                        finding_type=DataQualityFindingType.CONFLICTING_FINAL_CANDLE,
                        severity=DataQualitySeverity.HIGH,
                        symbol_id=symbol_id,
                        source_id=requested_source_id,
                        timeframe=timeframe.value,
                        timestamp=timestamp,
                        message="Final candles disagree on OHLCV values for the same timestamp",
                        expected_value="matching final candle values",
                        observed_value="conflicting final candle values",
                        metadata_json={
                            "sourceIds": sorted({str(candle.source_id) for candle in final_candles})
                        },
                    )
                )
                findings.append(
                    DetectedFinding(
                        finding_type=DataQualityFindingType.SOURCE_INCONSISTENCY,
                        severity=DataQualitySeverity.MEDIUM,
                        symbol_id=symbol_id,
                        source_id=requested_source_id,
                        timeframe=timeframe.value,
                        timestamp=timestamp,
                        message="Sources are inconsistent for the same final candle timestamp",
                        expected_value="consistent source values",
                        observed_value="source value disagreement",
                    )
                )
        return findings

    def detect_price_quality_findings(
        self,
        *,
        candles: list[Candle],
        symbol_id: UUID,
        requested_source_id: UUID | None,
        timeframe: Timeframe,
    ) -> list[DetectedFinding]:
        findings: list[DetectedFinding] = []
        sorted_candles = sorted(candles, key=lambda candle: candle.timestamp)
        ranges = [candle.high - candle.low for candle in sorted_candles]
        positive_ranges = [value for value in ranges if value > 0]
        average_range = (
            sum(positive_ranges, Decimal("0")) / Decimal(len(positive_ranges))
            if positive_ranges
            else Decimal("0")
        )
        for index, candle in enumerate(sorted_candles):
            candle_range = candle.high - candle.low
            if candle.volume == Decimal("0"):
                findings.append(
                    DetectedFinding(
                        finding_type=DataQualityFindingType.ZERO_VOLUME,
                        severity=DataQualitySeverity.LOW,
                        symbol_id=symbol_id,
                        source_id=candle.source_id,
                        timeframe=timeframe.value,
                        timestamp=candle.timestamp,
                        message="Final candle has zero volume",
                        expected_value=">0 or null",
                        observed_value="0",
                    )
                )
            if average_range > 0 and candle_range > average_range * self.outlier_range_multiplier:
                findings.append(
                    DetectedFinding(
                        finding_type=DataQualityFindingType.OUTLIER_RANGE,
                        severity=DataQualitySeverity.MEDIUM,
                        symbol_id=symbol_id,
                        source_id=candle.source_id,
                        timeframe=timeframe.value,
                        timestamp=candle.timestamp,
                        message="Candle range is abnormally large compared with local average",
                        expected_value=f"<={self.outlier_range_multiplier}x average range",
                        observed_value=str(candle_range),
                        metadata_json={"averageRange": str(average_range)},
                    )
                )
            if index == 0:
                continue
            previous = sorted_candles[index - 1]
            gap = abs(candle.open - previous.close)
            if average_range > 0 and gap > average_range * self.outlier_range_multiplier:
                findings.append(
                    DetectedFinding(
                        finding_type=DataQualityFindingType.INVALID_PRICE_GAP,
                        severity=DataQualitySeverity.MEDIUM,
                        symbol_id=symbol_id,
                        source_id=requested_source_id or candle.source_id,
                        timeframe=timeframe.value,
                        timestamp=candle.timestamp,
                        message="Open price gap is abnormally large compared with local range",
                        expected_value=f"<={self.outlier_range_multiplier}x average range",
                        observed_value=str(gap),
                        metadata_json={
                            "previousTimestamp": previous.timestamp.isoformat(),
                            "previousClose": str(previous.close),
                            "currentOpen": str(candle.open),
                            "averageRange": str(average_range),
                        },
                    )
                )
        return findings

    def build_result(
        self,
        *,
        findings: list[DetectedFinding],
        checked_candle_count: int,
        expected_candle_count: int,
        summary_subject: str,
        extra_metadata: dict[str, object],
    ) -> DetectionResult:
        score = Decimal("1.00000")
        for finding in findings:
            score -= FINDING_PENALTIES[finding.severity]
        score = min(max(score, Decimal("0.00000")), Decimal("1.00000")).quantize(Decimal("0.00001"))
        if expected_candle_count > 0 and checked_candle_count == 0:
            label = DataQualityLabel.INSUFFICIENT
        else:
            label = self.label_for_score(score)
        severity_counts = Counter(finding.severity.value for finding in findings)
        metadata = {
            "dataQualityVersion": self.data_quality_version,
            "expectedCandleCount": expected_candle_count,
            "severityCounts": dict(sorted(severity_counts.items())),
            "analysisUse": analysis_use_for_label(label, findings),
            **extra_metadata,
        }
        summary = (
            f"{summary_subject} completed with {len(findings)} findings and label {label.value}"
        )
        return DetectionResult(
            findings=findings,
            checked_candle_count=checked_candle_count,
            expected_candle_count=expected_candle_count,
            quality_score=score,
            quality_label=label,
            summary=summary,
            metadata_json=metadata,
        )

    def label_for_score(self, score: Decimal) -> DataQualityLabel:
        if score >= self.thresholds.strong:
            return DataQualityLabel.STRONG
        if score >= self.thresholds.acceptable:
            return DataQualityLabel.ACCEPTABLE
        if score >= self.thresholds.degraded:
            return DataQualityLabel.DEGRADED
        return DataQualityLabel.POOR


def expected_candle_count(start_time: datetime, end_time: datetime, timeframe: Timeframe) -> int:
    normalized_start = normalize_timestamp(start_time)
    normalized_end = normalize_timestamp(end_time)
    if normalized_start > normalized_end:
        return 0
    duration_seconds = int(timeframe_duration(timeframe).total_seconds())
    window_seconds = int((normalized_end - normalized_start).total_seconds())
    return (window_seconds // duration_seconds) + 1


def final_values_conflict(candles: list[Candle]) -> bool:
    values = {
        (
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
        )
        for candle in candles
    }
    return len(values) > 1


def seconds_since(value: datetime | None, now: datetime) -> int | None:
    if value is None:
        return None
    return max(int((now - normalize_timestamp(value)).total_seconds()), 0)


def analysis_use_for_label(
    label: DataQualityLabel,
    findings: list[DetectedFinding],
) -> dict[str, object]:
    has_critical = any(finding.severity == DataQualitySeverity.CRITICAL for finding in findings)
    has_high = any(finding.severity == DataQualitySeverity.HIGH for finding in findings)
    should_block = label in {DataQualityLabel.POOR, DataQualityLabel.INSUFFICIENT} or has_critical
    should_degrade = label == DataQualityLabel.DEGRADED or has_high
    if should_block:
        recommendation = "block"
    elif should_degrade:
        recommendation = "degrade"
    else:
        recommendation = "allow"
    return {
        "recommendation": recommendation,
        "reason": "Data quality only; not market prediction, trade advice, or execution guidance",
    }
