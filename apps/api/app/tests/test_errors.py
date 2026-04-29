import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_validation_error_shape() -> None:
    test_app = create_app(Settings(_env_file=None))

    @test_app.get("/validation-test")
    async def validation_test(value: int) -> dict[str, int]:
        return {"value": value}

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/validation-test", params={"value": "bad"})

    response_payload = response.json()
    assert response.status_code == 422
    assert response_payload["error"]["code"] == "validation_error"
    assert response_payload["error"]["message"] == "Request validation failed"
    assert "request_id" in response_payload["error"]
    assert response_payload["error"]["details"][0]["type"] == "int_parsing"


@pytest.mark.asyncio
async def test_unexpected_error_shape() -> None:
    test_app = create_app(Settings(_env_file=None))

    @test_app.get("/unexpected-test")
    async def unexpected_test() -> dict[str, str]:
        raise RuntimeError("hidden failure")

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/unexpected-test")

    response_payload = response.json()
    assert response.status_code == 500
    assert response_payload["error"]["code"] == "internal_error"
    assert response_payload["error"]["message"] == "Unexpected server error"
    assert "hidden failure" not in response.text
