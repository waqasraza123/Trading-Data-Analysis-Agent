import pytest
from pydantic import SecretStr

from app.core.rate_limit import (
    InMemoryRateLimiter,
    RateLimitBackendUnavailable,
    RedisRateLimiter,
    check_redis_connection,
    rate_limit_key,
)


class FakeRedis:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.counts: dict[str, int] = {}
        self.closed = False

    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object:
        if self.fail:
            raise RuntimeError("redis unavailable")
        key = str(keys_and_args[0])
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def ping(self) -> bool:
        if self.fail:
            raise RuntimeError("redis unavailable")
        return True

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_in_memory_rate_limiter_rejects_excess_requests() -> None:
    limiter = InMemoryRateLimiter()

    first_allowed = await limiter.allow("key", 1)
    second_allowed = await limiter.allow("key", 1)

    assert first_allowed is True
    assert second_allowed is False


@pytest.mark.asyncio
async def test_redis_rate_limiter_rejects_excess_requests() -> None:
    redis = FakeRedis()
    limiter = RedisRateLimiter(SecretStr("redis://localhost:6379/0"), client=redis)

    first_allowed = await limiter.allow("key", 1)
    second_allowed = await limiter.allow("key", 1)

    assert first_allowed is True
    assert second_allowed is False


@pytest.mark.asyncio
async def test_redis_rate_limiter_reports_backend_failure() -> None:
    limiter = RedisRateLimiter(
        SecretStr("redis://localhost:6379/0"),
        client=FakeRedis(fail=True),
    )

    with pytest.raises(RateLimitBackendUnavailable):
        await limiter.allow("key", 1)


@pytest.mark.asyncio
async def test_check_redis_connection_closes_client() -> None:
    redis = FakeRedis()

    def factory(redis_url: SecretStr) -> RedisRateLimiter:
        return RedisRateLimiter(redis_url, client=redis)

    is_healthy, message = await check_redis_connection(
        SecretStr("redis://localhost:6379/0"),
        client_factory=factory,
    )

    assert is_healthy is True
    assert message == "Redis connection succeeded"
    assert redis.closed is True


def test_rate_limit_key_uses_stable_request_scope() -> None:
    assert rate_limit_key("127.0.0.1", "POST", "/symbols") == (
        "rate-limit:127.0.0.1:POST:/symbols"
    )
