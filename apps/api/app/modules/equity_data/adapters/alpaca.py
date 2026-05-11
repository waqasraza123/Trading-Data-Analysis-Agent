from typing import Any
from urllib.parse import quote

from app.modules.equity_data.adapters.base import (
    EquityDataProvider,
    EquityMetadataItem,
    EquityProviderContext,
    EquityProviderResult,
    provider_not_configured,
)
from app.modules.equity_data.adapters.http import get_json, provider_http_failure
from app.modules.equity_data.normalizer import normalize_ticker, optional_bool


class AlpacaEquityDataProvider(EquityDataProvider):
    def key(self) -> str:
        return "alpaca"

    def label(self) -> str:
        return "Alpaca market data"

    def requires_credential_ref(self) -> bool:
        return True

    def supports_universe_import(self) -> bool:
        return True

    def supports_metadata_lookup(self) -> bool:
        return True

    def supports_fundamentals_snapshot(self) -> bool:
        return False

    def supports_earnings_calendar(self) -> bool:
        return False

    async def import_universe(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        if not self.ready(context):
            return provider_not_configured(self.key())
        filters = request.get("filters") if isinstance(request.get("filters"), dict) else {}
        query = {
            "status": filters.get("status") or "active",
            "asset_class": filters.get("asset_class") or "us_equity",
            "exchange": filters.get("exchange"),
        }
        try:
            payload = await get_json(
                context.base_url or "https://paper-api.alpaca.markets",
                "/v2/assets",
                query,
                self.headers(context),
                context.timeout_seconds,
                context.retry_attempts,
                context.retry_backoff_seconds,
            )
        except Exception as error:
            return provider_http_failure(self.key(), error)
        assets = payload if isinstance(payload, list) else []
        return EquityProviderResult(
            status="completed",
            metadata=[metadata_from_asset(item) for item in assets if isinstance(item, dict)],
            summary={
                "provider": self.key(),
                "endpoint": "assets",
                "received": len(assets),
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
        try:
            payload = await get_json(
                context.base_url or "https://paper-api.alpaca.markets",
                f"/v2/assets/{quote(ticker)}",
                {},
                self.headers(context),
                context.timeout_seconds,
                context.retry_attempts,
                context.retry_backoff_seconds,
            )
        except Exception as error:
            return provider_http_failure(self.key(), error)
        return EquityProviderResult(
            status="completed",
            metadata=[metadata_from_asset(payload)] if payload else [],
            summary={
                "provider": self.key(),
                "endpoint": "asset",
                "ticker": ticker,
            },
        )

    def ready(self, context: EquityProviderContext) -> bool:
        return (
            context.external_requests_enabled
            and context.credential_ref_id is not None
            and bool(context.credential_secrets.get("api_key_id"))
            and bool(context.credential_secrets.get("api_secret_key"))
        )

    def headers(self, context: EquityProviderContext) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": context.credential_secrets["api_key_id"],
            "APCA-API-SECRET-KEY": context.credential_secrets["api_secret_key"],
        }


def metadata_from_asset(item: dict[str, Any]) -> EquityMetadataItem:
    ticker = normalize_ticker(str(item.get("symbol") or item.get("ticker") or ""))
    return EquityMetadataItem(
        ticker=ticker,
        company_name=text_value(item.get("name"), 160) or ticker,
        exchange=text_value(item.get("exchange"), 80),
        sector=None,
        industry=text_value(item.get("class") or item.get("asset_class"), 160),
        country="us",
        currency=text_value(item.get("currency"), 16) or "USD",
        market_cap=None,
        average_volume=None,
        shares_float=None,
        is_etf=is_etf_asset(item),
        is_active=optional_bool(item.get("tradable")) is not False
        and str(item.get("status") or "").lower() != "inactive",
        raw_reference_json={"provider": "alpaca", "source": item},
    )


def text_value(value: object, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized[:max_length] or None


def is_etf_asset(item: dict[str, Any]) -> bool | None:
    normalized = " ".join(
        str(item.get(key) or "").lower()
        for key in ("name", "asset_class", "class", "attributes")
    )
    if not normalized.strip():
        return None
    if "etf" in normalized or "exchange traded fund" in normalized:
        return True
    return None
