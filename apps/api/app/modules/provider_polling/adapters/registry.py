from app.core.errors import AppError
from app.modules.provider_polling.adapters.base import ProviderPollingAdapter
from app.modules.provider_polling.adapters.binance_public_rest import (
    BinancePublicRestPollingAdapter,
)
from app.modules.provider_polling.adapters.generic_ohlc_http import GenericOhlcHttpPollingAdapter
from app.modules.provider_polling.adapters.mock import MockPollingProviderAdapter

PROVIDER_POLLING_ADAPTERS: dict[str, ProviderPollingAdapter] = {
    MockPollingProviderAdapter.provider_key: MockPollingProviderAdapter(),
    BinancePublicRestPollingAdapter.provider_key: BinancePublicRestPollingAdapter(),
    GenericOhlcHttpPollingAdapter.provider_key: GenericOhlcHttpPollingAdapter(),
}


def get_provider_polling_adapter(provider: str) -> ProviderPollingAdapter:
    adapter = PROVIDER_POLLING_ADAPTERS.get(provider.strip().lower())
    if adapter is None:
        raise AppError(422, "unsupported_provider_polling_provider", "Provider is not supported")
    return adapter
