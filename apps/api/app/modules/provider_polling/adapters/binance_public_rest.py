import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.modules.provider_polling.adapters.base import (
    ProviderPollingAdapter,
    ProviderPollingAdapterException,
    ProviderPollingFetchRequest,
    ProviderPollingResult,
)
from app.modules.provider_polling.schemas import (
    ProviderCandle,
    ProviderPollingErrorItem,
)


class BinancePublicRestPollingAdapter(ProviderPollingAdapter):
    provider_key = "binance_public_rest"

    async def fetch_candles(
        self,
        request: ProviderPollingFetchRequest,
    ) -> ProviderPollingResult:
        url = build_klines_url(request)
        payload = await asyncio.to_thread(
            fetch_json_payload,
            url,
            request.timeout_seconds,
            request.user_agent,
        )
        if not isinstance(payload, list):
            raise ProviderPollingAdapterException(
                "invalid_binance_response",
                "Binance response must be a list of klines",
            )
        candles: list[ProviderCandle] = []
        errors: list[ProviderPollingErrorItem] = []
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        for index, item in enumerate(payload, start=1):
            try:
                candles.append(parse_kline_item(item, request, now_ms))
            except (InvalidOperation, ValueError, TypeError, IndexError) as error:
                errors.append(
                    ProviderPollingErrorItem(
                        code="invalid_binance_kline",
                        message=f"Binance kline at position {index} could not be parsed",
                        raw_item_json=raw_item_to_json(item, error),
                    )
                )
        return ProviderPollingResult(
            candles=candles,
            provider_metadata={
                "provider": self.provider_key,
                "requested_url": url,
                "responseCount": len(payload),
            },
            warnings=[],
            errors=errors,
        )


def build_klines_url(request: ProviderPollingFetchRequest) -> str:
    params: dict[str, str | int] = {
        "symbol": request.provider_symbol.upper(),
        "interval": request.timeframe.value,
        "limit": request.limit,
    }
    if request.start_time is not None:
        params["startTime"] = milliseconds_from_datetime(request.start_time)
    if request.end_time is not None:
        params["endTime"] = milliseconds_from_datetime(request.end_time)
    return f"{request.binance_public_rest_base_url.rstrip('/')}/api/v3/klines?{urlencode(params)}"


def fetch_json_payload(url: str, timeout_seconds: int, user_agent: str) -> object:
    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise ProviderPollingAdapterException(
            "binance_http_error",
            f"Binance request failed with HTTP status {error.code}",
        ) from error
    except URLError as error:
        raise ProviderPollingAdapterException(
            "binance_network_error",
            "Binance request failed before a response was received",
        ) from error
    except json.JSONDecodeError as error:
        raise ProviderPollingAdapterException(
            "invalid_binance_json",
            "Binance response was not valid JSON",
        ) from error


def parse_kline_item(
    item: object,
    request: ProviderPollingFetchRequest,
    now_ms: int,
) -> ProviderCandle:
    if not isinstance(item, list):
        msg = "Binance kline item must be a list"
        raise TypeError(msg)
    open_time_ms = int(item[0])
    close_time_ms = int(item[6])
    return ProviderCandle(
        provider_symbol=request.provider_symbol.upper(),
        timeframe=request.timeframe,
        timestamp=datetime.fromtimestamp(open_time_ms / 1000, tz=UTC),
        open=Decimal(str(item[1])),
        high=Decimal(str(item[2])),
        low=Decimal(str(item[3])),
        close=Decimal(str(item[4])),
        volume=Decimal(str(item[5])),
        is_final=close_time_ms <= now_ms,
        raw_item_json={
            "openTime": open_time_ms,
            "open": str(item[1]),
            "high": str(item[2]),
            "low": str(item[3]),
            "close": str(item[4]),
            "volume": str(item[5]),
            "closeTime": close_time_ms,
        },
    )


def milliseconds_from_datetime(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)


def raw_item_to_json(item: object, error: Exception) -> dict[str, Any]:
    if isinstance(item, dict):
        return {"item": item, "error": str(error)}
    if isinstance(item, list):
        return {"item": [str(value) for value in item], "error": str(error)}
    return {"item": str(item), "error": str(error)}
