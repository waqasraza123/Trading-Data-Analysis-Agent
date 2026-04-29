from app.core.errors import AppError
from app.modules.live.providers.base import LiveProvider
from app.modules.live.providers.binance import BinanceLiveProvider
from app.modules.live.providers.mock import MockLiveProvider

LIVE_PROVIDERS: dict[str, LiveProvider] = {
    MockLiveProvider.name: MockLiveProvider(),
    BinanceLiveProvider.name: BinanceLiveProvider(),
}


def get_live_provider(provider_name: str) -> LiveProvider:
    provider = LIVE_PROVIDERS.get(provider_name.lower())
    if provider is None:
        raise AppError(422, "unsupported_live_provider", "Live provider is not supported")
    return provider
