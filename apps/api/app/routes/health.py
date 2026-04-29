from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from app.db.session import check_database_connection

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        environment=settings.app_env.value,
    )


@router.get("/health/db", response_model=DatabaseHealthResponse)
async def database_health(request: Request, response: Response) -> DatabaseHealthResponse:
    settings = request.app.state.settings
    database_is_healthy, _ = await check_database_connection(settings)
    if database_is_healthy:
        return DatabaseHealthResponse(status="healthy", database="healthy")
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return DatabaseHealthResponse(status="unhealthy", database="unhealthy")
