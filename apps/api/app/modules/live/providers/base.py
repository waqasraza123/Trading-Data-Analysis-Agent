from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping

from app.modules.live.schemas import LiveProviderMessage, NormalizedLiveProviderEvent


class LiveProviderRuntimeError(Exception):
    pass


class LiveProviderDisconnectedError(LiveProviderRuntimeError):
    pass


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

    async def receive_message(
        self,
        symbol: str,
        timeframe: str,
        config_json: Mapping[str, object],
    ) -> LiveProviderMessage:
        raise NotImplementedError

    async def stream_messages(
        self,
        symbol: str,
        timeframe: str,
        config_json: Mapping[str, object],
    ) -> AsyncIterator[LiveProviderMessage]:
        while True:
            yield await self.receive_message(symbol, timeframe, config_json)

    @abstractmethod
    def normalize_message(self, payload: LiveProviderMessage) -> NormalizedLiveProviderEvent:
        raise NotImplementedError
