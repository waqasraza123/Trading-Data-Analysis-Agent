from typing import Any

from app.modules.equity_data.adapters.base import (
    EquityDataProvider,
    EquityProviderContext,
    EquityProviderResult,
    provider_not_configured,
    provider_not_implemented,
)


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
        return self.external_stub(context)

    async def lookup_symbol_metadata(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return self.external_stub(context)

    async def fetch_fundamentals_snapshot(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return self.external_stub(context)

    async def fetch_earnings_events(
        self,
        context: EquityProviderContext,
        request: dict[str, Any],
    ) -> EquityProviderResult:
        return self.external_stub(context)

    def external_stub(self, context: EquityProviderContext) -> EquityProviderResult:
        if not context.external_requests_enabled or context.credential_ref_id is None:
            return provider_not_configured(self.key())
        return provider_not_implemented(self.key())
