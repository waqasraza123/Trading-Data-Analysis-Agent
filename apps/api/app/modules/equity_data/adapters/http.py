import asyncio
import json
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.modules.equity_data.adapters.base import EquityProviderResult


async def get_json(
    base_url: str,
    path: str,
    query: Mapping[str, object],
    headers: Mapping[str, str],
    timeout_seconds: int,
    retry_attempts: int = 1,
    retry_backoff_seconds: float = 0.5,
) -> Any:
    url = build_url(base_url, path, query)
    attempts = max(1, retry_attempts)
    for attempt in range(1, attempts + 1):
        try:
            return await asyncio.to_thread(fetch_json_sync, url, headers, timeout_seconds)
        except EquityProviderHttpError as error:
            if attempt >= attempts or not error.retryable:
                raise
            await asyncio.sleep(retry_delay(error, retry_backoff_seconds, attempt))
    raise EquityProviderHttpError(None, "Provider request failed")


def build_url(base_url: str, path: str, query: Mapping[str, object]) -> str:
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    filtered_query = {
        key: value
        for key, value in query.items()
        if value is not None and value != "" and value != []
    }
    if not filtered_query:
        return f"{normalized_base}{normalized_path}"
    return f"{normalized_base}{normalized_path}?{urlencode(filtered_query, doseq=True)}"


def fetch_json_sync(
    url: str,
    headers: Mapping[str, str],
    timeout_seconds: int,
) -> Any:
    request = Request(url, headers=dict(headers), method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
    except HTTPError as error:
        raise EquityProviderHttpError(
            error.code,
            safe_error_body(error),
            retry_after_seconds(error.headers.get("Retry-After")),
        ) from error
    except URLError as error:
        reason = getattr(error, "reason", None)
        raise EquityProviderHttpError(None, str(reason or "Provider request failed")) from error
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EquityProviderHttpError(None, "Provider returned invalid JSON") from error
    return decoded


def provider_http_failure(provider: str, error: Exception) -> EquityProviderResult:
    if isinstance(error, EquityProviderHttpError):
        return EquityProviderResult(
            status="failed",
            summary={
                "provider": provider,
                "httpStatus": error.status_code,
                "errorType": "provider_http_error",
                "retryable": error.retryable,
            },
            error_message=error.message,
        )
    return EquityProviderResult(
        status="failed",
        summary={"provider": provider, "errorType": type(error).__name__},
        error_message="Provider request failed",
    )


def safe_error_body(error: HTTPError) -> str:
    try:
        body = error.read(1000).decode("utf-8", errors="replace")
    except Exception:
        body = ""
    return body.strip() or f"Provider returned HTTP {error.code}"


class EquityProviderHttpError(Exception):
    def __init__(
        self,
        status_code: int | None,
        message: str,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message[:1000]
        self.retry_after_seconds = retry_after_seconds
        self.retryable = status_code == 429 or (
            status_code is not None and 500 <= status_code <= 599
        )


def retry_delay(
    error: EquityProviderHttpError,
    retry_backoff_seconds: float,
    attempt: int,
) -> float:
    if error.retry_after_seconds is not None:
        return min(max(error.retry_after_seconds, 0), 60)
    return min(max(retry_backoff_seconds, 0) * (2 ** max(attempt - 1, 0)), 60)


def retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None
