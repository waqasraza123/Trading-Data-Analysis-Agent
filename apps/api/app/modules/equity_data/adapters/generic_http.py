from typing import Any

from app.modules.equity_data.adapters.base import (
    EquityDataProvider,
    EquityProviderContext,
    EquityProviderResult,
    provider_not_configured,
)


class GenericHttpEquityDataProvider(EquityDataProvider):
    def key(self) -> str:
        return "generic_http"

    def label(self) -> str:
        return "Generic HTTP equity data"

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
        return provider_not_configured(self.key())

    async def lookup_symbol_metadata(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return provider_not_configured(self.key())

    async def fetch_fundamentals_snapshot(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return provider_not_configured(self.key())

    async def fetch_earnings_events(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return provider_not_configured(self.key())
