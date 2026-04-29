import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.config import AppEnvironment, Settings
from app.core.errors import create_error_response, get_request_id


@dataclass
class RateLimitBucket:
    window_started_at: float
    request_count: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self.buckets: dict[str, RateLimitBucket] = {}

    def allow(self, key: str, now: float, requests_per_minute: int) -> bool:
        bucket = self.buckets.get(key)
        if bucket is None or now - bucket.window_started_at >= 60:
            self.buckets[key] = RateLimitBucket(window_started_at=now, request_count=1)
            return True
        if bucket.request_count >= requests_per_minute:
            return False
        bucket.request_count += 1
        return True


class OperationsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self.rate_limiter = InMemoryRateLimiter()
        self.logger = logging.getLogger(settings.service_name)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started_at = time.perf_counter()
        request_id = self.resolve_request_id(request)
        request.state.request_id = request_id
        response: Response | None = None
        try:
            response = self.guard_request(request)
            if response is None:
                response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
        except Exception:
            request.state.error_code = "internal_error"
            self.log_request(request, 500, started_at, failed=True)
            raise
        finally:
            if response is not None:
                failed = response.status_code >= 400
                self.log_request(request, response.status_code, started_at, failed=failed)

    def resolve_request_id(self, request: Request) -> str:
        header_value = request.headers.get("x-request-id")
        if header_value is None or header_value.strip() == "":
            return str(uuid4())
        return header_value.strip()[:128]

    def guard_request(self, request: Request) -> Response | None:
        size_response = self.enforce_request_size(request)
        if size_response is not None:
            return size_response
        auth_response = self.enforce_api_key(request)
        if auth_response is not None:
            return auth_response
        rate_limit_response = self.enforce_rate_limit(request)
        if rate_limit_response is not None:
            return rate_limit_response
        return None

    def enforce_request_size(self, request: Request) -> Response | None:
        content_length = request.headers.get("content-length")
        if content_length is None:
            return None
        try:
            request_size = int(content_length)
        except ValueError:
            return None
        content_type = request.headers.get("content-type", "")
        is_upload = content_type.startswith("multipart/form-data")
        limit = (
            self.settings.max_upload_file_bytes
            if is_upload
            else self.settings.max_request_body_bytes
        )
        if request_size <= limit:
            return None
        code = "upload_file_too_large" if is_upload else "request_body_too_large"
        message = "Upload file is too large" if is_upload else "Request body is too large"
        request.state.error_code = code
        return create_error_response(request, 413, code, message)

    def enforce_api_key(self, request: Request) -> Response | None:
        if not self.settings.auth_enabled:
            return None
        if self.is_public_path(request.url.path) or request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        configured_key = self.settings.admin_api_key
        if configured_key is None:
            request.state.error_code = "api_key_not_configured"
            return create_error_response(
                request,
                500,
                "api_key_not_configured",
                "API key authentication is not configured",
            )
        supplied_key = request.headers.get(self.settings.api_key_header_name, "")
        valid_key = secrets.compare_digest(
            supplied_key,
            configured_key.get_secret_value(),
        )
        if valid_key:
            return None
        request.state.error_code = "invalid_api_key"
        return create_error_response(request, 401, "invalid_api_key", "Invalid API key")

    def enforce_rate_limit(self, request: Request) -> Response | None:
        if not self.settings.rate_limit_enabled:
            return None
        if self.is_public_path(request.url.path) or request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        if self.settings.app_env not in {
            AppEnvironment.DEVELOPMENT,
            AppEnvironment.TEST,
        }:
            request.state.error_code = "rate_limit_backend_not_configured"
            return create_error_response(
                request,
                503,
                "rate_limit_backend_not_configured",
                "Rate limit backend is not configured",
            )
        key = f"{self.client_host(request)}:{request.method}:{request.url.path}"
        allowed = self.rate_limiter.allow(
            key,
            time.monotonic(),
            self.settings.rate_limit_requests_per_minute,
        )
        if allowed:
            return None
        request.state.error_code = "rate_limit_exceeded"
        return create_error_response(request, 429, "rate_limit_exceeded", "Rate limit exceeded")

    def is_public_path(self, path: str) -> bool:
        prefix = self.settings.api_prefix
        if prefix and path.startswith(prefix):
            path = path[len(prefix) :] or "/"
        return path == "/health" or path.startswith("/health/")

    def client_host(self, request: Request) -> str | None:
        if request.client is None:
            return None
        return request.client.host

    def log_request(
        self,
        request: Request,
        status_code: int,
        started_at: float,
        failed: bool,
    ) -> None:
        event_name = "request_failed" if failed else "request_completed"
        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        log_method = self.logger.warning if failed else self.logger.info
        log_method(
            event_name,
            extra={
                "request_id": get_request_id(request),
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_host": self.client_host(request),
                "error_code": getattr(request.state, "error_code", None),
            },
        )
