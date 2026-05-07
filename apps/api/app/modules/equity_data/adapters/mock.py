from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.modules.equity_data.adapters.base import (
    EquityDataProvider,
    EquityEarningsItem,
    EquityFundamentalsItem,
    EquityMetadataItem,
    EquityProviderContext,
    EquityProviderResult,
)
from app.modules.equity_data.normalizer import normalize_ticker


class MockEquityDataProvider(EquityDataProvider):
    def key(self) -> str:
        return "mock_equity_data"

    def label(self) -> str:
        return "Mock equity data"

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
        limit = int(request.get("filters", {}).get("limit") or len(sample_metadata()))
        rows = sample_metadata()[: max(1, min(limit, len(sample_metadata())))]
        return EquityProviderResult(
            status="completed",
            metadata=rows,
            summary={"provider": self.key(), "generated": True, "count": len(rows)},
        )

    async def lookup_symbol_metadata(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        ticker = normalize_ticker(str(request.get("ticker")))
        rows = [row for row in sample_metadata() if row.ticker == ticker]
        if not rows:
            rows = [
                EquityMetadataItem(
                    ticker=ticker,
                    company_name=f"{ticker} Sample Company",
                    exchange="NASDAQ",
                    sector="Technology",
                    industry="Software",
                    country="US",
                    currency="USD",
                    average_volume=Decimal("750000"),
                    raw_reference_json={"provider": self.key(), "generated": True},
                )
            ]
        return EquityProviderResult(
            status="completed",
            metadata=rows,
            summary={"provider": self.key(), "ticker": ticker, "count": len(rows)},
        )

    async def fetch_fundamentals_snapshot(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        ticker = normalize_ticker(str(request.get("ticker")))
        now = datetime.now(UTC)
        metadata = next((row for row in sample_metadata() if row.ticker == ticker), None)
        item = EquityFundamentalsItem(
            ticker=ticker,
            snapshot_time=now,
            market_cap=metadata.market_cap if metadata else Decimal("25000000000"),
            average_volume=metadata.average_volume if metadata else Decimal("900000"),
            relative_volume=Decimal("1.0800"),
            beta=Decimal("1.1500"),
            pe_ratio=Decimal("31.5000"),
            eps=Decimal("5.4200"),
            revenue_growth=Decimal("0.0800"),
            earnings_growth=Decimal("0.0600"),
            debt_to_equity=Decimal("0.4200"),
            free_cash_flow=Decimal("1200000000"),
            raw_reference_json={"provider": self.key(), "generated": True},
        )
        return EquityProviderResult(
            status="completed",
            fundamentals=[item],
            summary={"provider": self.key(), "ticker": ticker, "count": 1},
        )

    async def fetch_earnings_events(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        ticker = normalize_ticker(str(request.get("ticker")))
        today = datetime.now(UTC).date()
        items = [
            EquityEarningsItem(
                ticker=ticker,
                event_date=today + timedelta(days=14),
                fiscal_period="FY2026 Q2",
                report_time="after_market",
                eps_estimate=Decimal("1.2400"),
                revenue_estimate=Decimal("8200000000"),
                importance="high",
                status="scheduled",
                raw_reference_json={"provider": self.key(), "generated": True, "sequence": 1},
            ),
            EquityEarningsItem(
                ticker=ticker,
                event_date=today - timedelta(days=76),
                fiscal_period="FY2026 Q1",
                report_time="after_market",
                eps_estimate=Decimal("1.1100"),
                eps_actual=Decimal("1.1600"),
                revenue_estimate=Decimal("7900000000"),
                revenue_actual=Decimal("8050000000"),
                importance="medium",
                status="reported",
                raw_reference_json={"provider": self.key(), "generated": True, "sequence": 2},
            ),
        ]
        return EquityProviderResult(
            status="completed",
            earnings=items,
            summary={"provider": self.key(), "ticker": ticker, "count": len(items)},
        )


def sample_metadata() -> list[EquityMetadataItem]:
    return [
        EquityMetadataItem(
            ticker="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ",
            sector="Technology",
            industry="Consumer Electronics",
            country="US",
            currency="USD",
            market_cap=Decimal("3000000000000"),
            average_volume=Decimal("52000000"),
            shares_float=Decimal("15330000000"),
            is_etf=False,
            raw_reference_json={"provider": "mock_equity_data", "index": "sample"},
        ),
        EquityMetadataItem(
            ticker="MSFT",
            company_name="Microsoft Corporation",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software Infrastructure",
            country="US",
            currency="USD",
            market_cap=Decimal("2800000000000"),
            average_volume=Decimal("24500000"),
            shares_float=Decimal("7430000000"),
            is_etf=False,
            raw_reference_json={"provider": "mock_equity_data", "index": "sample"},
        ),
        EquityMetadataItem(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            exchange="NASDAQ",
            sector="Technology",
            industry="Semiconductors",
            country="US",
            currency="USD",
            market_cap=Decimal("2200000000000"),
            average_volume=Decimal("41000000"),
            shares_float=Decimal("24600000000"),
            is_etf=False,
            raw_reference_json={"provider": "mock_equity_data", "index": "sample"},
        ),
        EquityMetadataItem(
            ticker="SPY",
            company_name="SPDR S&P 500 ETF Trust",
            exchange="NYSEARCA",
            sector="ETF",
            industry="Broad Market ETF",
            country="US",
            currency="USD",
            market_cap=Decimal("500000000000"),
            average_volume=Decimal("65000000"),
            is_etf=True,
            raw_reference_json={"provider": "mock_equity_data", "index": "sample"},
        ),
    ]
