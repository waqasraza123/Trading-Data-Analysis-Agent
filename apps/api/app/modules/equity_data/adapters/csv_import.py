from datetime import UTC, datetime
from typing import Any

from app.modules.equity_data.adapters.base import (
    EquityDataProvider,
    EquityEarningsItem,
    EquityMetadataItem,
    EquityProviderContext,
    EquityProviderResult,
)
from app.modules.equity_data.normalizer import (
    optional_bool,
    optional_decimal,
    optional_text,
    parse_event_date,
    safe_reference,
    snake_or_camel,
)


class CsvEquityImportProvider(EquityDataProvider):
    def key(self) -> str:
        return "csv_equity_import"

    def label(self) -> str:
        return "CSV or JSON rows"

    def supports_universe_import(self) -> bool:
        return True

    def supports_metadata_lookup(self) -> bool:
        return True

    def supports_earnings_calendar(self) -> bool:
        return True

    async def import_universe(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        rows = request.get("rows")
        if not isinstance(rows, list):
            return EquityProviderResult(
                status="failed",
                error_message="Rows are required",
                summary={"provider": self.key(), "count": 0},
            )
        metadata = [metadata_from_row(row) for row in rows if isinstance(row, dict)]
        return EquityProviderResult(
            status="completed",
            metadata=metadata,
            summary={"provider": self.key(), "count": len(metadata), "received": len(rows)},
        )

    async def lookup_symbol_metadata(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        row = request.get("row")
        if not isinstance(row, dict):
            return EquityProviderResult(
                status="provider_not_configured",
                error_message="CSV metadata lookup requires an inline row",
                summary={"provider": self.key()},
            )
        return EquityProviderResult(
            status="completed",
            metadata=[metadata_from_row(row)],
            summary={"provider": self.key(), "count": 1},
        )

    async def fetch_earnings_events(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        rows = request.get("rows")
        if not isinstance(rows, list):
            return EquityProviderResult(
                status="failed",
                error_message="Rows are required",
                summary={"provider": self.key(), "count": 0},
            )
        earnings = [earnings_from_row(row) for row in rows if isinstance(row, dict)]
        return EquityProviderResult(
            status="completed",
            earnings=earnings,
            summary={"provider": self.key(), "count": len(earnings), "received": len(rows)},
        )


def metadata_from_row(row: dict[str, Any]) -> EquityMetadataItem:
    return EquityMetadataItem(
        ticker=str(row["ticker"]).strip().upper(),
        company_name=optional_text(snake_or_camel(row, "company_name", "companyName"), 160),
        exchange=optional_text(row.get("exchange"), 80),
        sector=optional_text(row.get("sector"), 120),
        industry=optional_text(row.get("industry"), 160),
        country=optional_text(row.get("country"), 80),
        currency=optional_text(row.get("currency"), 16),
        market_cap=optional_decimal(snake_or_camel(row, "market_cap", "marketCap")),
        average_volume=optional_decimal(snake_or_camel(row, "average_volume", "averageVolume")),
        shares_float=optional_decimal(snake_or_camel(row, "shares_float", "sharesFloat")),
        is_etf=optional_bool(snake_or_camel(row, "is_etf", "isEtf")),
        is_active=optional_bool(snake_or_camel(row, "is_active", "isActive")) is not False,
        raw_reference_json=safe_reference(
            row.get("raw_reference_json") or row.get("rawReferenceJson") or row
        ),
    )


def earnings_from_row(row: dict[str, Any]) -> EquityEarningsItem:
    return EquityEarningsItem(
        ticker=str(row.get("ticker") or "").strip().upper(),
        event_date=parse_event_date(snake_or_camel(row, "event_date", "eventDate")),
        fiscal_period=optional_text(snake_or_camel(row, "fiscal_period", "fiscalPeriod"), 32),
        report_time=optional_text(snake_or_camel(row, "report_time", "reportTime"), 32),
        eps_estimate=optional_decimal(snake_or_camel(row, "eps_estimate", "epsEstimate")),
        eps_actual=optional_decimal(snake_or_camel(row, "eps_actual", "epsActual")),
        revenue_estimate=optional_decimal(
            snake_or_camel(row, "revenue_estimate", "revenueEstimate")
        ),
        revenue_actual=optional_decimal(snake_or_camel(row, "revenue_actual", "revenueActual")),
        importance=str(row.get("importance") or "unknown"),
        status=str(row.get("status") or "unknown"),
        raw_reference_json=safe_reference(
            row.get("raw_reference_json")
            or row.get("rawReferenceJson")
            or {"provider": "csv_equity_import", "importedAt": datetime.now(UTC).isoformat()}
        ),
    )
