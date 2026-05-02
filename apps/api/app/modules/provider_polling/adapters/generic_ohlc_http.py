from app.modules.provider_polling.adapters.base import (
    ProviderPollingAdapter,
    ProviderPollingFetchRequest,
    ProviderPollingResult,
)
from app.modules.provider_polling.schemas import ProviderPollingErrorItem, ProviderPollingWarning


class GenericOhlcHttpPollingAdapter(ProviderPollingAdapter):
    provider_key = "generic_ohlc_http"

    async def fetch_candles(
        self,
        request: ProviderPollingFetchRequest,
    ) -> ProviderPollingResult:
        return ProviderPollingResult(
            candles=[],
            provider_metadata={
                "provider": self.provider_key,
                "requested_url": None,
                "configured": False,
            },
            warnings=[
                ProviderPollingWarning(
                    code="generic_adapter_stub",
                    message=(
                        "Generic OHLC HTTP polling requires provider-specific mapping before use"
                    ),
                )
            ],
            errors=[
                ProviderPollingErrorItem(
                    code="generic_adapter_not_configured",
                    message="Generic OHLC HTTP adapter is a safe stub and did not fetch candles",
                    raw_item_json=None,
                )
            ],
        )
