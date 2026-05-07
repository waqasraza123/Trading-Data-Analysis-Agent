from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class EquityProviderContext:
    workspace_id: str
    credential_ref_id: str | None
    external_requests_enabled: bool
    timeout_seconds: int


@dataclass(frozen=True)
class EquityMetadataItem:
    ticker: str
    company_name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    currency: str | None = None
    market_cap: Decimal | None = None
    average_volume: Decimal | None = None
    shares_float: Decimal | None = None
    is_etf: bool | None = None
    is_active: bool = True
    raw_reference_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EquityFundamentalsItem:
    ticker: str
    snapshot_time: datetime
    market_cap: Decimal | None = None
    average_volume: Decimal | None = None
    relative_volume: Decimal | None = None
    beta: Decimal | None = None
    pe_ratio: Decimal | None = None
    eps: Decimal | None = None
    revenue_growth: Decimal | None = None
    earnings_growth: Decimal | None = None
    debt_to_equity: Decimal | None = None
    free_cash_flow: Decimal | None = None
    raw_reference_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EquityEarningsItem:
    ticker: str
    event_date: date
    fiscal_period: str | None = None
    report_time: str | None = None
    eps_estimate: Decimal | None = None
    eps_actual: Decimal | None = None
    revenue_estimate: Decimal | None = None
    revenue_actual: Decimal | None = None
    importance: str = "unknown"
    status: str = "unknown"
    raw_reference_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EquityProviderResult:
    status: str
    metadata: list[EquityMetadataItem] = field(default_factory=list)
    fundamentals: list[EquityFundamentalsItem] = field(default_factory=list)
    earnings: list[EquityEarningsItem] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class EquityDataProvider(ABC):
    @abstractmethod
    def key(self) -> str:
        raise NotImplementedError

    def label(self) -> str:
        return self.key()

    def requires_credential_ref(self) -> bool:
        return False

    def supports_universe_import(self) -> bool:
        return False

    def supports_metadata_lookup(self) -> bool:
        return False

    def supports_fundamentals_snapshot(self) -> bool:
        return False

    def supports_earnings_calendar(self) -> bool:
        return False

    async def import_universe(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return provider_not_implemented(self.key())

    async def lookup_symbol_metadata(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return provider_not_implemented(self.key())

    async def fetch_fundamentals_snapshot(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return provider_not_implemented(self.key())

    async def fetch_earnings_events(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return provider_not_implemented(self.key())


def provider_not_implemented(provider: str) -> EquityProviderResult:
    return EquityProviderResult(
        status="provider_not_implemented",
        summary={"provider": provider, "implemented": False},
        error_message="Provider capability is not implemented",
    )


def provider_not_configured(provider: str) -> EquityProviderResult:
    return EquityProviderResult(
        status="provider_not_configured",
        summary={"provider": provider, "configured": False},
        error_message="Provider is not configured",
    )
