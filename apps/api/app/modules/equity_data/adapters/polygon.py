from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from app.modules.equity_data.adapters.base import (
    EquityDataProvider,
    EquityEarningsItem,
    EquityFundamentalsItem,
    EquityMetadataItem,
    EquityProviderContext,
    EquityProviderResult,
    provider_not_configured,
)
from app.modules.equity_data.adapters.http import get_json, provider_http_failure
from app.modules.equity_data.normalizer import normalize_ticker, optional_bool


class PolygonEquityDataProvider(EquityDataProvider):
    def key(self) -> str:
        return "polygon"

    def label(self) -> str:
        return "Polygon"

    def requires_credential_ref(self) -> bool:
        return True

    def supports_universe_import(self) -> bool:
        return True

    def supports_metadata_lookup(self) -> bool:
        return True

    def supports_fundamentals_snapshot(self) -> bool:
        return True

    def supports_earnings_calendar(self) -> bool:
        return True

    async def import_universe(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        if not self.ready(context):
            return provider_not_configured(self.key())
        filters = dict_value(request.get("filters"))
        limit = bounded_limit(filters.get("limit"), 100, 1000)
        query = {
            "market": filters.get("market") or "stocks",
            "active": filters.get("active", "true"),
            "type": filters.get("type"),
            "ticker.gte": filters.get("ticker_gte") or filters.get("ticker.gte"),
            "ticker.lt": filters.get("ticker_lt") or filters.get("ticker.lt"),
            "limit": limit,
            "sort": filters.get("sort") or "ticker",
            "apiKey": context.credential_secrets["api_key"],
        }
        try:
            raw_payload = await get_json(
                context.base_url or "https://api.polygon.io",
                "/v3/reference/tickers",
                query,
                {},
                context.timeout_seconds,
            )
        except Exception as error:
            return provider_http_failure(self.key(), error)
        payload = dict_value(raw_payload)
        results = list_value(payload.get("results"))
        return EquityProviderResult(
            status="completed",
            metadata=[
                metadata_from_ticker(item)
                for item in results
                if isinstance(item, dict) and item.get("ticker")
            ],
            summary={
                "provider": self.key(),
                "endpoint": "reference_tickers",
                "received": len(results),
                "count": payload.get("count"),
                "requestId": payload.get("request_id"),
                "hasNextPage": bool(payload.get("next_url")),
            },
        )

    async def lookup_symbol_metadata(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        if not self.ready(context):
            return provider_not_configured(self.key())
        ticker = normalize_ticker(str(request.get("ticker") or ""))
        filters = dict_value(request.get("filters"))
        query = {"date": filters.get("date"), "apiKey": context.credential_secrets["api_key"]}
        try:
            raw_payload = await get_json(
                context.base_url or "https://api.polygon.io",
                f"/v3/reference/tickers/{quote(ticker)}",
                query,
                {},
                context.timeout_seconds,
            )
        except Exception as error:
            return provider_http_failure(self.key(), error)
        payload = dict_value(raw_payload)
        result = dict_value(payload.get("results"))
        return EquityProviderResult(
            status="completed",
            metadata=[metadata_from_ticker(result)] if result else [],
            summary={
                "provider": self.key(),
                "endpoint": "ticker_overview",
                "ticker": ticker,
                "requestId": payload.get("request_id"),
            },
        )

    async def fetch_fundamentals_snapshot(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        if not self.ready(context):
            return provider_not_configured(self.key())
        ticker = normalize_ticker(str(request.get("ticker") or ""))
        filters = dict_value(request.get("filters"))
        query = {
            "ticker": ticker,
            "limit": bounded_limit(filters.get("limit"), 1, 10),
            "apiKey": context.credential_secrets["api_key"],
        }
        try:
            raw_payload = await get_json(
                context.base_url or "https://api.polygon.io",
                "/stocks/financials/v1/ratios",
                query,
                {},
                context.timeout_seconds,
            )
        except Exception as error:
            return provider_http_failure(self.key(), error)
        payload = dict_value(raw_payload)
        results = list_value(payload.get("results"))
        fundamentals = [
            fundamentals_from_ratio(ticker, item)
            for item in results[:1]
            if isinstance(item, dict)
        ]
        return EquityProviderResult(
            status="completed",
            fundamentals=fundamentals,
            summary={
                "provider": self.key(),
                "endpoint": "financial_ratios",
                "ticker": ticker,
                "received": len(results),
                "requestId": payload.get("request_id"),
            },
        )

    async def fetch_earnings_events(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        if not self.ready(context):
            return provider_not_configured(self.key())
        ticker = normalize_ticker(str(request.get("ticker") or ""))
        filters = dict_value(request.get("filters"))
        query = {
            "ticker": ticker,
            "date": filters.get("date"),
            "date.gte": filters.get("date_gte") or filters.get("date.gte"),
            "date.lte": filters.get("date_lte") or filters.get("date.lte"),
            "limit": bounded_limit(filters.get("limit"), 25, 1000),
            "sort": filters.get("sort") or "date.desc",
            "apiKey": context.credential_secrets["api_key"],
        }
        try:
            raw_payload = await get_json(
                context.base_url or "https://api.polygon.io",
                "/benzinga/v1/earnings",
                query,
                {},
                context.timeout_seconds,
            )
        except Exception as error:
            return provider_http_failure(self.key(), error)
        payload = dict_value(raw_payload)
        results = list_value(payload.get("results"))
        earnings = [earnings_from_polygon(item) for item in results if isinstance(item, dict)]
        return EquityProviderResult(
            status="completed",
            earnings=[item for item in earnings if item is not None],
            summary={
                "provider": self.key(),
                "endpoint": "benzinga_earnings",
                "ticker": ticker,
                "received": len(results),
                "requestId": payload.get("request_id"),
                "hasNextPage": bool(payload.get("next_url")),
            },
        )

    def ready(self, context: EquityProviderContext) -> bool:
        return (
            context.external_requests_enabled
            and context.credential_ref_id is not None
            and bool(context.credential_secrets.get("api_key"))
        )


def metadata_from_ticker(item: dict[str, Any]) -> EquityMetadataItem:
    ticker = normalize_ticker(str(item.get("ticker") or ""))
    return EquityMetadataItem(
        ticker=ticker,
        company_name=text_value(item.get("name"), 160),
        exchange=text_value(item.get("primary_exchange") or item.get("exchange"), 80),
        sector=text_value(item.get("sic_description"), 120),
        industry=text_value(item.get("type"), 160),
        country=text_value(item.get("locale"), 80),
        currency=text_value(item.get("currency_name") or item.get("currency"), 16),
        market_cap=safe_decimal(item.get("market_cap")),
        average_volume=None,
        shares_float=safe_decimal(
            item.get("share_class_shares_outstanding")
            or item.get("weighted_shares_outstanding")
        ),
        is_etf=is_etf_type(item.get("type")),
        is_active=optional_bool(item.get("active")) is not False,
        raw_reference_json=provider_reference("polygon", item),
    )


def fundamentals_from_ratio(ticker: str, item: dict[str, Any]) -> EquityFundamentalsItem:
    snapshot_time = parse_datetime(item.get("as_of_date") or item.get("date"))
    return EquityFundamentalsItem(
        ticker=ticker,
        snapshot_time=snapshot_time,
        market_cap=safe_decimal(first_present(item, "market_cap", "marketCapitalization")),
        average_volume=safe_decimal(first_present(item, "average_volume", "averageVolume")),
        relative_volume=safe_decimal(first_present(item, "relative_volume", "relativeVolume")),
        beta=safe_decimal(first_present(item, "beta")),
        pe_ratio=safe_decimal(first_present(item, "price_to_earnings", "pe_ratio", "peRatio")),
        eps=safe_decimal(first_present(item, "earnings_per_share", "eps")),
        revenue_growth=safe_decimal(first_present(item, "revenue_growth", "revenueGrowth")),
        earnings_growth=safe_decimal(first_present(item, "earnings_growth", "earningsGrowth")),
        debt_to_equity=safe_decimal(first_present(item, "debt_to_equity", "debtToEquity")),
        free_cash_flow=safe_decimal(first_present(item, "free_cash_flow", "freeCashFlow")),
        raw_reference_json=provider_reference("polygon", item),
    )


def earnings_from_polygon(item: dict[str, Any]) -> EquityEarningsItem | None:
    event_date = item.get("date")
    ticker = item.get("ticker")
    if not event_date or not ticker:
        return None
    try:
        parsed_date = datetime.fromisoformat(str(event_date)[:10]).date()
    except ValueError:
        return None
    return EquityEarningsItem(
        ticker=normalize_ticker(str(ticker)),
        event_date=parsed_date,
        fiscal_period=text_value(item.get("fiscal_period"), 32),
        report_time=text_value(item.get("time") or item.get("date_status"), 32),
        eps_estimate=safe_decimal(item.get("estimated_eps")),
        eps_actual=safe_decimal(item.get("actual_eps")),
        revenue_estimate=safe_decimal(item.get("estimated_revenue")),
        revenue_actual=safe_decimal(item.get("actual_revenue")),
        importance=importance_from_polygon(item.get("importance")),
        status=status_from_polygon(item),
        raw_reference_json=provider_reference("polygon", item),
    )


def dict_value(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def text_value(value: object, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized[:max_length] or None


def safe_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def bounded_limit(value: object, default: int, maximum: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def is_etf_type(value: object) -> bool | None:
    normalized = str(value or "").lower()
    if not normalized:
        return None
    return "etf" in normalized or "fund" in normalized


def parse_datetime(value: object) -> datetime:
    if value is None:
        return datetime.now(UTC)
    try:
        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now(UTC)


def first_present(item: dict[str, Any], *keys: str) -> object:
    for key in keys:
        if key in item:
            return item[key]
    return None


def importance_from_polygon(value: object) -> str:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return "unknown"
    if parsed >= 4:
        return "high"
    if parsed >= 2:
        return "medium"
    return "low"


def status_from_polygon(item: dict[str, Any]) -> str:
    if item.get("actual_eps") is not None or item.get("actual_revenue") is not None:
        return "reported"
    if str(item.get("date_status") or "").lower() in {"confirmed", "projected"}:
        return "scheduled"
    return "unknown"


def provider_reference(provider: str, item: dict[str, Any]) -> dict[str, Any]:
    return {"provider": provider, "source": item}
