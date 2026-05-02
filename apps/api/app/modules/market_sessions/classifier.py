from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.modules.market_sessions.models import MarketSessionLabel, MarketSessionRegion
from app.modules.symbols.models import MarketType


@dataclass(frozen=True)
class MarketSessionClassification:
    session_label: MarketSessionLabel
    session_region: MarketSessionRegion
    overlap_label: str | None
    is_weekend: bool
    is_market_open: bool
    reference_time: datetime
    timezone: str
    summary: str
    metadata_json: dict[str, object]


def classify_market_session(
    reference_time: datetime,
    market_type: str,
    timezone_name: str,
    session_version: str,
) -> MarketSessionClassification:
    resolved_time = normalize_reference_time(reference_time)
    configured_timezone = normalize_timezone(timezone_name)
    local_time = resolved_time.astimezone(ZoneInfo(configured_timezone))
    hour = resolved_time.hour
    minute = resolved_time.minute
    weekend = resolved_time.weekday() in {5, 6}
    metadata: dict[str, object] = {
        "model": "rough_utc_session_windows",
        "sessionVersion": session_version,
        "utcHour": hour,
        "utcMinute": minute,
        "utcWeekday": resolved_time.weekday(),
        "configuredTimezone": configured_timezone,
        "localReferenceTime": local_time.isoformat(),
        "limitations": [],
    }
    if market_type == MarketType.CRYPTO.value:
        metadata["limitations"] = [
            "Crypto is modeled as 24/7 because no exchange maintenance calendar is configured."
        ]
        return MarketSessionClassification(
            session_label=MarketSessionLabel.CRYPTO_24_7,
            session_region=MarketSessionRegion.CRYPTO,
            overlap_label=None,
            is_weekend=weekend,
            is_market_open=True,
            reference_time=resolved_time,
            timezone=configured_timezone,
            summary="Crypto 24/7 market context.",
            metadata_json=metadata,
        )
    if market_type == MarketType.FOREX.value:
        return classify_forex_session(
            reference_time=resolved_time,
            timezone_name=configured_timezone,
            hour=hour,
            minute=minute,
            weekend=weekend,
            metadata_json=metadata,
        )
    return classify_calendar_limited_market(
        reference_time=resolved_time,
        timezone_name=configured_timezone,
        market_type=market_type,
        weekend=weekend,
        metadata_json=metadata,
    )


def classify_forex_session(
    reference_time: datetime,
    timezone_name: str,
    hour: int,
    minute: int,
    weekend: bool,
    metadata_json: dict[str, object],
) -> MarketSessionClassification:
    if weekend:
        return MarketSessionClassification(
            session_label=MarketSessionLabel.WEEKEND,
            session_region=MarketSessionRegion.GLOBAL,
            overlap_label=None,
            is_weekend=True,
            is_market_open=False,
            reference_time=reference_time,
            timezone=timezone_name,
            summary="Forex weekend context in UTC.",
            metadata_json=metadata_json,
        )
    minutes = hour * 60 + minute
    if 7 * 60 <= minutes < 8 * 60:
        return forex_result(
            MarketSessionLabel.ASIA_LONDON_OVERLAP,
            MarketSessionRegion.GLOBAL,
            "asia_london_overlap",
            reference_time,
            timezone_name,
            metadata_json,
            "Forex Asia/London overlap context in UTC.",
        )
    if 12 * 60 <= minutes < 16 * 60:
        return forex_result(
            MarketSessionLabel.LONDON_NEW_YORK_OVERLAP,
            MarketSessionRegion.GLOBAL,
            "london_new_york_overlap",
            reference_time,
            timezone_name,
            metadata_json,
            "Forex London/New York overlap context in UTC.",
        )
    if 0 <= minutes < 8 * 60:
        return forex_result(
            MarketSessionLabel.ASIA,
            MarketSessionRegion.ASIA,
            None,
            reference_time,
            timezone_name,
            metadata_json,
            "Forex Asia session context in UTC.",
        )
    if 8 * 60 <= minutes < 12 * 60:
        return forex_result(
            MarketSessionLabel.LONDON,
            MarketSessionRegion.EUROPE,
            None,
            reference_time,
            timezone_name,
            metadata_json,
            "Forex London session context in UTC.",
        )
    if 16 * 60 <= minutes < 21 * 60:
        return forex_result(
            MarketSessionLabel.NEW_YORK,
            MarketSessionRegion.US,
            None,
            reference_time,
            timezone_name,
            metadata_json,
            "Forex New York session context in UTC.",
        )
    return MarketSessionClassification(
        session_label=MarketSessionLabel.OFF_SESSION,
        session_region=MarketSessionRegion.GLOBAL,
        overlap_label=None,
        is_weekend=False,
        is_market_open=False,
        reference_time=reference_time,
        timezone=timezone_name,
        summary="Forex off-session context in UTC.",
        metadata_json=metadata_json,
    )


def forex_result(
    session_label: MarketSessionLabel,
    session_region: MarketSessionRegion,
    overlap_label: str | None,
    reference_time: datetime,
    timezone_name: str,
    metadata_json: dict[str, object],
    summary: str,
) -> MarketSessionClassification:
    return MarketSessionClassification(
        session_label=session_label,
        session_region=session_region,
        overlap_label=overlap_label,
        is_weekend=False,
        is_market_open=True,
        reference_time=reference_time,
        timezone=timezone_name,
        summary=summary,
        metadata_json=metadata_json,
    )


def classify_calendar_limited_market(
    reference_time: datetime,
    timezone_name: str,
    market_type: str,
    weekend: bool,
    metadata_json: dict[str, object],
) -> MarketSessionClassification:
    metadata_json["limitations"] = [
        "No external exchange calendar is configured.",
        "Session context for stocks, indices, and commodities is intentionally cautious.",
    ]
    if weekend:
        return MarketSessionClassification(
            session_label=MarketSessionLabel.WEEKEND,
            session_region=MarketSessionRegion.UNKNOWN,
            overlap_label=None,
            is_weekend=True,
            is_market_open=False,
            reference_time=reference_time,
            timezone=timezone_name,
            summary=f"{market_type} weekend context without exchange calendar.",
            metadata_json=metadata_json,
        )
    return MarketSessionClassification(
        session_label=MarketSessionLabel.UNKNOWN,
        session_region=MarketSessionRegion.UNKNOWN,
        overlap_label=None,
        is_weekend=False,
        is_market_open=False,
        reference_time=reference_time,
        timezone=timezone_name,
        summary=f"{market_type} session unknown without exchange calendar.",
        metadata_json=metadata_json,
    )


def normalize_reference_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_timezone(value: str) -> str:
    normalized_value = value.strip() or "UTC"
    try:
        ZoneInfo(normalized_value)
    except ZoneInfoNotFoundError:
        return "UTC"
    return normalized_value
