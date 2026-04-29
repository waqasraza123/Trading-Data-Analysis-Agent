import logging

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.config import AppEnvironment, Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_api_key_guard_disabled_by_default() -> None:
    test_app = create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST))

    @test_app.post("/guard-test")
    async def guard_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.post("/guard-test")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_key_guard_rejects_invalid_key_when_enabled() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            auth_enabled=True,
            admin_api_key=SecretStr("correct-key"),
        )
    )

    @test_app.post("/guard-test")
    async def guard_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.post("/guard-test", headers={"x-admin-api-key": "wrong-key"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


@pytest.mark.asyncio
async def test_api_key_guard_accepts_valid_key_when_enabled() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            auth_enabled=True,
            admin_api_key=SecretStr("correct-key"),
        )
    )

    @test_app.post("/guard-test")
    async def guard_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/guard-test",
            headers={"x-admin-api-key": "correct-key"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_routes_remain_public_when_api_key_guard_enabled() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            auth_enabled=True,
            admin_api_key=SecretStr("correct-key"),
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        health_response = await client.get("/health")
        live_response = await client.get("/health/live")

    assert health_response.status_code == 200
    assert live_response.status_code == 200


@pytest.mark.asyncio
async def test_request_logging_does_not_log_secrets(caplog: pytest.LogCaptureFixture) -> None:
    secret_value = "correct-key"
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            auth_enabled=True,
            admin_api_key=SecretStr(secret_value),
        )
    )

    @test_app.post("/logging-test")
    async def logging_test() -> dict[str, str]:
        return {"status": "ok"}

    caplog.set_level(logging.INFO, logger="trading-intelligence-api")
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/logging-test",
            headers={"x-admin-api-key": secret_value},
            content=f"token={secret_value}",
        )

    assert response.status_code == 200
    assert "request_completed" in caplog.text
    assert secret_value not in caplog.text


@pytest.mark.asyncio
async def test_request_limit_returns_clean_error() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            max_request_body_bytes=5,
        )
    )

    @test_app.post("/body-test")
    async def body_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.post("/body-test", content="too-large")

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["code"] == "request_body_too_large"
    assert "requestId" in payload["error"]


@pytest.mark.asyncio
async def test_upload_limit_returns_clean_error() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            max_upload_file_bytes=5,
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/imports/candles/csv",
            files={"file": ("candles.csv", b"too-large", "text/csv")},
            data={
                "workspace_id": "00000000-0000-0000-0000-000000000001",
                "source_id": "00000000-0000-0000-0000-000000000002",
                "symbol_id": "00000000-0000-0000-0000-000000000003",
                "timeframe": "1m",
            },
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "upload_file_too_large"


@pytest.mark.asyncio
async def test_rate_limit_disabled_behavior() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            rate_limit_enabled=False,
            rate_limit_requests_per_minute=1,
        )
    )

    @test_app.post("/rate-test")
    async def rate_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        first_response = await client.post("/rate-test")
        second_response = await client.post("/rate-test")

    assert first_response.status_code == 200
    assert second_response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_enabled_rejects_excess_requests() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            rate_limit_enabled=True,
            rate_limit_requests_per_minute=1,
        )
    )

    @test_app.post("/rate-test")
    async def rate_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        first_response = await client.post("/rate-test")
        second_response = await client.post("/rate-test")

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["error"]["code"] == "rate_limit_exceeded"
