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
