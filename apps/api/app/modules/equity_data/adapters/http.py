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
) -> Any:
    url = build_url(base_url, path, query)
    return await asyncio.to_thread(fetch_json_sync, url, headers, timeout_seconds)


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
        raise EquityProviderHttpError(error.code, safe_error_body(error)) from error
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
    def __init__(self, status_code: int | None, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message[:1000]
