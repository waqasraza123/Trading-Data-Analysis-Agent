from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, build_async_database_url
from app.core.errors import AppError
from app.modules.observability.metrics import (
    collect_observability_metrics,
    observability_metrics_to_prometheus,
)
from app.modules.observability.schemas import (
    ObservabilityMetricsRead,
    ServiceSloRead,
    ServiceSloSnapshotRead,
    TracingStatusRead,
)
from app.modules.observability.slo import calculate_service_slo, persist_service_slo_snapshot
from app.modules.observability.tracing import tracing_status

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics_text(
    request: Request,
    workspace_id: Annotated[UUID | None, Query()] = None,
) -> PlainTextResponse:
    settings: Settings = request.app.state.settings
    ensure_metrics_enabled(settings)
    async with optional_observability_session(settings) as session:
        metrics = await collect_observability_metrics(settings, session, workspace_id)
    return PlainTextResponse(
        observability_metrics_to_prometheus(metrics),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/metrics.json", response_model=ObservabilityMetricsRead)
async def get_metrics_json(
    request: Request,
    workspace_id: Annotated[UUID | None, Query()] = None,
) -> ObservabilityMetricsRead:
    settings: Settings = request.app.state.settings
    ensure_metrics_enabled(settings)
    async with optional_observability_session(settings) as session:
        return await collect_observability_metrics(settings, session, workspace_id)


@router.get("/slo", response_model=ServiceSloRead)
async def get_slo_status(
    request: Request,
    workspace_id: Annotated[UUID | None, Query()] = None,
) -> ServiceSloRead:
    settings: Settings = request.app.state.settings
    ensure_observability_enabled(settings)
    async with optional_observability_session(settings) as session:
        return await calculate_service_slo(settings, session, workspace_id)


@router.post(
    "/slo/snapshot",
    response_model=ServiceSloSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_slo_snapshot(
    request: Request,
    workspace_id: Annotated[UUID | None, Query()] = None,
) -> ServiceSloSnapshotRead:
    settings: Settings = request.app.state.settings
    ensure_observability_enabled(settings)
    if settings.database_url is None:
        raise AppError(
            503,
            "database_not_configured",
            "DATABASE_URL is required to persist SLO snapshots",
        )
    async with optional_observability_session(settings) as session:
        if session is None:
            raise AppError(
                503,
                "database_not_configured",
                "DATABASE_URL is required to persist SLO snapshots",
            )
        slo = await calculate_service_slo(settings, session, workspace_id)
        snapshot = await persist_service_slo_snapshot(session, slo)
        return ServiceSloSnapshotRead.model_validate(snapshot)


@router.get("/tracing/status", response_model=TracingStatusRead)
async def get_tracing_status(request: Request) -> TracingStatusRead:
    settings: Settings = request.app.state.settings
    ensure_observability_enabled(settings)
    return tracing_status(settings)


def ensure_observability_enabled(settings: Settings) -> None:
    if not settings.observability_enabled:
        raise AppError(404, "observability_disabled", "Observability endpoints are disabled")


def ensure_metrics_enabled(settings: Settings) -> None:
    ensure_observability_enabled(settings)
    if not settings.metrics_endpoint_enabled:
        raise AppError(404, "metrics_endpoint_disabled", "Metrics endpoints are disabled")


@asynccontextmanager
async def optional_observability_session(
    settings: Settings,
) -> AsyncIterator[AsyncSession | None]:
    if settings.database_url is None:
        yield None
        return
    engine = create_async_engine(
        build_async_database_url(settings.database_url),
        pool_pre_ping=True,
    )
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()
