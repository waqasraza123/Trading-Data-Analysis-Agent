import time
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from inspect import isawaitable
from typing import Protocol, cast

from pydantic import SecretStr

from app.config import Settings


@dataclass
class RateLimitBucket:
    window_started_at: float
    request_count: int


class RateLimitBackendUnavailable(RuntimeError):
    pass


class RateLimiter(Protocol):
    backend_name: str

    async def allow(self, key: str, requests_per_minute: int) -> bool:
        ...

    async def close(self) -> None:
        ...


class AsyncRedisClient(Protocol):
    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object:
        ...

    async def ping(self) -> object:
        ...


class InMemoryRateLimiter:
    backend_name = "memory"

    def __init__(self) -> None:
        self.buckets: dict[str, RateLimitBucket] = {}

    async def allow(self, key: str, requests_per_minute: int) -> bool:
        now = time.monotonic()
        bucket = self.buckets.get(key)
        if bucket is None or now - bucket.window_started_at >= 60:
            self.buckets[key] = RateLimitBucket(window_started_at=now, request_count=1)
            return True
        if bucket.request_count >= requests_per_minute:
            return False
        bucket.request_count += 1
        return True

    async def close(self) -> None:
        self.buckets.clear()


class RedisRateLimiter:
    backend_name = "redis"
    window_seconds = 60
    increment_script = (
        'local current = redis.call("INCR", KEYS[1]) '
        'if current == 1 then redis.call("EXPIRE", KEYS[1], ARGV[1]) end '
        "return current"
    )

    def __init__(self, redis_url: SecretStr, client: AsyncRedisClient | None = None) -> None:
        self.redis_url = redis_url
        self.client = client

    async def allow(self, key: str, requests_per_minute: int) -> bool:
        try:
            client = self.get_client()
            count = await client.eval(self.increment_script, 1, key, self.window_seconds)
        except Exception as exc:
            raise RateLimitBackendUnavailable("Redis rate limit backend is unavailable") from exc
        return int(str(count)) <= requests_per_minute

    async def ping(self) -> bool:
        try:
            client = self.get_client()
            result = await client.ping()
        except Exception as exc:
            raise RateLimitBackendUnavailable("Redis health check failed") from exc
        return bool(result)

    async def close(self) -> None:
        if self.client is None:
            return
        close = getattr(self.client, "aclose", None)
        if close is None:
            close = getattr(self.client, "close", None)
        if close is None:
            return
        result = close()
        if isawaitable(result):
            await result

    def get_client(self) -> AsyncRedisClient:
        if self.client is not None:
            return self.client
        redis_asyncio = import_module("redis.asyncio")
        self.client = cast(
            AsyncRedisClient,
            redis_asyncio.from_url(
                self.redis_url.get_secret_value(),
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            ),
        )
        return self.client


def create_rate_limiter(settings: Settings) -> RateLimiter:
    if settings.redis_url is not None:
        return RedisRateLimiter(settings.redis_url)
    return InMemoryRateLimiter()


def rate_limit_key(client_host: str | None, method: str, path: str) -> str:
    normalized_host = client_host or "unknown"
    return f"rate-limit:{normalized_host}:{method}:{path}"


async def check_redis_connection(
    redis_url: SecretStr | None,
    client_factory: Callable[[SecretStr], RedisRateLimiter] = RedisRateLimiter,
) -> tuple[bool, str]:
    if redis_url is None:
        return False, "REDIS_URL is not configured"
    limiter = client_factory(redis_url)
    try:
        await limiter.ping()
    except RateLimitBackendUnavailable:
        return False, "Redis connection failed"
    finally:
        await limiter.close()
    return True, "Redis connection succeeded"
