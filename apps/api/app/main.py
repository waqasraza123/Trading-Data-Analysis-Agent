import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.core.errors import RequestIdMiddleware, register_error_handlers
from app.core.logging import configure_logging
from app.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = app.state.settings
    configure_logging(settings.log_level)
    app.state.logger = logging.getLogger(settings.service_name)
    app.state.logger.info(
        "app_startup",
        extra={"app_env": settings.app_env.value, "service": settings.service_name},
    )
    yield
    app.state.logger.info(
        "app_shutdown",
        extra={"app_env": settings.app_env.value, "service": settings.service_name},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.service_title,
        version=resolved_settings.service_version,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.logger = logging.getLogger(resolved_settings.service_name)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(health_router, prefix=resolved_settings.api_prefix)
    return app


app = create_app()
