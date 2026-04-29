from abc import ABC, abstractmethod

from app.modules.live.schemas import LiveProviderMessage, NormalizedLiveProviderEvent


class LiveProvider(ABC):
    name: str

    async def connect(self) -> None:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError

    async def subscribe(self, symbol: str, timeframe: str) -> None:
        raise NotImplementedError

    async def unsubscribe(self, symbol: str, timeframe: str) -> None:
        raise NotImplementedError

    async def handle_message(self, payload: LiveProviderMessage) -> NormalizedLiveProviderEvent:
        return self.normalize_message(payload)

    @abstractmethod
    def normalize_message(self, payload: LiveProviderMessage) -> NormalizedLiveProviderEvent:
        raise NotImplementedError
