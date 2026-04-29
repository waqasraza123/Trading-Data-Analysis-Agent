from datetime import UTC, datetime, timedelta
from enum import StrEnum


class Timeframe(StrEnum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


TIMEFRAME_DURATIONS: dict[Timeframe, timedelta] = {
    Timeframe.ONE_MINUTE: timedelta(minutes=1),
    Timeframe.FIVE_MINUTES: timedelta(minutes=5),
    Timeframe.FIFTEEN_MINUTES: timedelta(minutes=15),
    Timeframe.THIRTY_MINUTES: timedelta(minutes=30),
    Timeframe.ONE_HOUR: timedelta(hours=1),
    Timeframe.FOUR_HOURS: timedelta(hours=4),
    Timeframe.ONE_DAY: timedelta(days=1),
}


def normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def timeframe_duration(timeframe: Timeframe) -> timedelta:
    return TIMEFRAME_DURATIONS[timeframe]


def timestamp_aligns_with_timeframe(timestamp: datetime, timeframe: Timeframe) -> bool:
    normalized_timestamp = normalize_timestamp(timestamp)
    duration = timeframe_duration(timeframe)
    seconds_since_day_start = (
        normalized_timestamp.hour * 3600
        + normalized_timestamp.minute * 60
        + normalized_timestamp.second
    )
    duration_seconds = int(duration.total_seconds())
    return (
        normalized_timestamp.microsecond == 0
        and seconds_since_day_start % duration_seconds == 0
    )


def expected_timestamps(
    start_time: datetime,
    end_time: datetime,
    timeframe: Timeframe,
) -> list[datetime]:
    normalized_start_time = normalize_timestamp(start_time)
    normalized_end_time = normalize_timestamp(end_time)
    duration = timeframe_duration(timeframe)
    timestamps: list[datetime] = []
    current_timestamp = normalized_start_time
    while current_timestamp <= normalized_end_time:
        timestamps.append(current_timestamp)
        current_timestamp += duration
    return timestamps
