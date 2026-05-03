from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class QuietHoursDecision:
    inside_quiet_hours: bool
    behavior: str
    reason: str | None = None


def evaluate_quiet_hours(
    quiet_hours_json: dict[str, object],
    now: datetime,
    default_timezone: str,
) -> QuietHoursDecision:
    if not bool(quiet_hours_json.get("enabled", False)):
        return QuietHoursDecision(inside_quiet_hours=False, behavior="deliver")
    timezone_name = str(quiet_hours_json.get("timezone") or default_timezone)
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo(default_timezone)
    local_now = now.astimezone(timezone)
    days = quiet_hours_json.get("days")
    if isinstance(days, list) and days:
        allowed_days = {
            int(day) for day in days if isinstance(day, int | str) and str(day).isdigit()
        }
        if local_now.weekday() not in allowed_days:
            return QuietHoursDecision(inside_quiet_hours=False, behavior="deliver")
    start = parse_quiet_time(quiet_hours_json.get("start"))
    end = parse_quiet_time(quiet_hours_json.get("end"))
    if start is None or end is None:
        return QuietHoursDecision(inside_quiet_hours=False, behavior="deliver")
    inside = is_time_in_range(local_now.time(), start, end)
    behavior = str(quiet_hours_json.get("behavior") or "hold").strip().lower()
    if behavior not in {"hold", "skip"}:
        behavior = "hold"
    return QuietHoursDecision(
        inside_quiet_hours=inside,
        behavior=behavior if inside else "deliver",
        reason="quiet_hours" if inside else None,
    )


def parse_quiet_time(value: object) -> time | None:
    if not isinstance(value, str):
        return None
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return time(hour=hour, minute=minute)


def is_time_in_range(value: time, start: time, end: time) -> bool:
    if start == end:
        return True
    if start < end:
        return start <= value < end
    return value >= start or value < end
