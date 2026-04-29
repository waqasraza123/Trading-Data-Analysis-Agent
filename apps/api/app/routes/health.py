from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings, build_async_database_url
from app.db.session import check_database_connection
from app.modules.live.operational import LiveWorkerHealth, collect_live_worker_health

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str


class ReadyHealthResponse(BaseModel):
    status: str
    database: str
    configuration: str


class WorkerStatusResponse(BaseModel):
    status: str
    database: str
    live_feed_worker: LiveWorkerHealth | dict[str, str]
    stale_monitor: dict[str, str]
    redis: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        environment=settings.app_env.value,
    )


@router.get("/health/live", response_model=HealthResponse)
async def live_health(request: Request) -> HealthResponse:
    return await health(request)


@router.get("/health/db", response_model=DatabaseHealthResponse)
async def database_health(request: Request, response: Response) -> DatabaseHealthResponse:
    settings = request.app.state.settings
    database_is_healthy, message = await check_database_connection(settings)
    if database_is_healthy:
        return DatabaseHealthResponse(status="healthy", database="healthy")
    request.app.state.logger.warning("db_health_failed", extra={"reason": message})
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return DatabaseHealthResponse(status="unhealthy", database="unhealthy")


@router.get("/health/ready", response_model=ReadyHealthResponse)
async def ready_health(request: Request, response: Response) -> ReadyHealthResponse:
    settings = request.app.state.settings
    database_is_healthy, message = await check_database_connection(settings)
    if database_is_healthy:
        return ReadyHealthResponse(
            status="ready",
            database="healthy",
            configuration="ready",
        )
    request.app.state.logger.warning("db_health_failed", extra={"reason": message})
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyHealthResponse(
        status="unready",
        database="unhealthy",
        configuration="ready",
    )


@router.get("/health/workers", response_model=WorkerStatusResponse)
async def workers_health(request: Request, response: Response) -> WorkerStatusResponse:
    settings: Settings = request.app.state.settings
    database_is_healthy, _ = await check_database_connection(settings)
    redis_status = "not_configured" if settings.redis_url is None else "not_checked"
    if not database_is_healthy or settings.database_url is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return WorkerStatusResponse(
            status="degraded",
            database="unhealthy",
            live_feed_worker={"status": "not_configured"},
            stale_monitor={"status": "not_configured"},
            redis={"status": redis_status},
        )
    engine = create_async_engine(
        build_async_database_url(settings.database_url),
        pool_pre_ping=True,
    )
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            live_worker_health = await collect_live_worker_health(session)
    finally:
        await engine.dispose()
    worker_status = live_worker_health.status
    response_status = "healthy" if worker_status in {"healthy", "not_running"} else "degraded"
    if response_status == "degraded":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return WorkerStatusResponse(
        status=response_status,
        database="healthy",
        live_feed_worker=live_worker_health,
        stale_monitor={"status": "available"},
        redis={"status": redis_status},
    )
