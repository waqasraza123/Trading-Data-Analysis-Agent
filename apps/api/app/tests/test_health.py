import pytest
from httpx import ASGITransport, AsyncClient

from app.config import AppEnvironment, Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_health_returns_service_status() -> None:
    test_app = create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST))

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "trading-intelligence-api",
        "environment": "test",
    }


@pytest.mark.asyncio
async def test_database_health_handles_missing_database_url() -> None:
    test_app = create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST))

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "database": "unhealthy"}


@pytest.mark.asyncio
async def test_live_health_works_without_database() -> None:
    test_app = create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST))

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_ready_health_handles_missing_database_url() -> None:
    test_app = create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST))

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unready",
        "database": "unhealthy",
        "configuration": "ready",
    }


@pytest.mark.asyncio
async def test_worker_health_returns_safe_status_without_database() -> None:
    test_app = create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST))

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/workers")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["database"] == "unhealthy"
    assert payload["live_feed_worker"]["status"] == "not_configured"
