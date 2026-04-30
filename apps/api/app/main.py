import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import OperationsMiddleware
from app.modules.action_plans.routes import router as action_plans_router
from app.modules.analysis.routes import router as analysis_router
from app.modules.candles.routes import router as candles_router
from app.modules.chart_screenshots.routes import router as chart_screenshot_router
from app.modules.data_sources.routes import router as data_sources_router
from app.modules.engine_versions.routes import router as engine_versions_router
from app.modules.explanations.routes import router as explanations_router
from app.modules.imports.routes import router as imports_router
from app.modules.live.routes import router as live_router
from app.modules.llm_explanations.routes import router as llm_explanations_router
from app.modules.news.routes import news_events_router
from app.modules.news.routes import router as news_router
from app.modules.outcomes.routes import router as outcomes_router
from app.modules.profile_diagnostics.routes import router as profile_diagnostics_router
from app.modules.reasoning.routes import router as reasoning_router
from app.modules.signals.routes import router as signals_router
from app.modules.strategy_profiles.routes import router as strategy_profiles_router
from app.modules.symbols.routes import router as symbols_router
from app.modules.users.routes import router as users_router
from app.modules.workspaces.routes import router as workspaces_router
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
    if resolved_settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_allowed_origins,
            allow_credentials=resolved_settings.cors_allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(OperationsMiddleware, settings=resolved_settings)
    register_error_handlers(app)
    app.include_router(health_router, prefix=resolved_settings.api_prefix)
    app.include_router(workspaces_router, prefix=resolved_settings.api_prefix)
    app.include_router(users_router, prefix=resolved_settings.api_prefix)
    app.include_router(symbols_router, prefix=resolved_settings.api_prefix)
    app.include_router(data_sources_router, prefix=resolved_settings.api_prefix)
    app.include_router(engine_versions_router, prefix=resolved_settings.api_prefix)
    app.include_router(imports_router, prefix=resolved_settings.api_prefix)
    app.include_router(live_router, prefix=resolved_settings.api_prefix)
    app.include_router(candles_router, prefix=resolved_settings.api_prefix)
    app.include_router(chart_screenshot_router, prefix=resolved_settings.api_prefix)
    app.include_router(analysis_router, prefix=resolved_settings.api_prefix)
    app.include_router(strategy_profiles_router, prefix=resolved_settings.api_prefix)
    app.include_router(signals_router, prefix=resolved_settings.api_prefix)
    app.include_router(news_events_router, prefix=resolved_settings.api_prefix)
    app.include_router(news_router, prefix=resolved_settings.api_prefix)
    app.include_router(explanations_router, prefix=resolved_settings.api_prefix)
    app.include_router(llm_explanations_router, prefix=resolved_settings.api_prefix)
    app.include_router(outcomes_router, prefix=resolved_settings.api_prefix)
    app.include_router(profile_diagnostics_router, prefix=resolved_settings.api_prefix)
    app.include_router(reasoning_router, prefix=resolved_settings.api_prefix)
    app.include_router(action_plans_router, prefix=resolved_settings.api_prefix)
    return app


app = create_app()
