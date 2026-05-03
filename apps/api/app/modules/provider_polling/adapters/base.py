from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.modules.candles.timeframes import Timeframe
from app.modules.provider_polling.schemas import (
    ProviderCandle,
    ProviderPollingErrorItem,
    ProviderPollingWarning,
)


@dataclass(frozen=True)
class ProviderPollingFetchRequest:
    provider: str
    provider_symbol: str
    timeframe: Timeframe
    start_time: datetime | None
    end_time: datetime | None
    limit: int
    timeout_seconds: int
    user_agent: str
    binance_public_rest_base_url: str
    request_metadata_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderPollingResult:
    candles: list[ProviderCandle]
    provider_metadata: dict[str, Any]
    warnings: list[ProviderPollingWarning]
    errors: list[ProviderPollingErrorItem]


class ProviderPollingAdapterException(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ProviderPollingAdapter(ABC):
    provider_key: str

    @abstractmethod
    async def fetch_candles(
        self,
        request: ProviderPollingFetchRequest,
    ) -> ProviderPollingResult:
        raise NotImplementedError
