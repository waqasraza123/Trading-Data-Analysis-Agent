from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.news.schemas import (
    NewsCorrelationRead,
    NewsCorrelationRunRead,
    NewsEventCreate,
    NewsEventImportRead,
    NewsEventRead,
    NewsEventUpdate,
)
from app.modules.news.service import NewsCorrelationService, NewsEventService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["news"])
news_events_router = APIRouter(prefix="/news-events", tags=["news-events"])


def get_news_event_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> NewsEventService:
    return NewsEventService(session)


def get_news_correlation_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> NewsCorrelationService:
    return NewsCorrelationService(session)


@news_events_router.post(
    "",
    response_model=NewsEventRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def create_news_event(
    payload: NewsEventCreate,
    service: Annotated[NewsEventService, Depends(get_news_event_service)],
) -> NewsEventRead:
    event = await service.create_event(payload)
    return NewsEventRead.model_validate(event)


@news_events_router.post(
    "/import-json",
    response_model=NewsEventImportRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def import_news_events(
    payload: list[NewsEventCreate],
    service: Annotated[NewsEventService, Depends(get_news_event_service)],
) -> NewsEventImportRead:
    events = await service.import_events(payload)
    return NewsEventImportRead(
        imported_count=len(events),
        events=[NewsEventRead.model_validate(event) for event in events],
    )


@news_events_router.get("", response_model=list[NewsEventRead])
async def list_news_events(
    service: Annotated[NewsEventService, Depends(get_news_event_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
    currency: str | None = None,
    asset: str | None = None,
    symbol_id: UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[NewsEventRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    events = await service.list_events(
        limit=pagination.limit,
        offset=pagination.offset,
        workspace_id=workspace_id,
        currency=currency,
        asset=asset,
        symbol_id=symbol_id,
        start_time=start_time,
        end_time=end_time,
    )
    return [NewsEventRead.model_validate(event) for event in events]


@news_events_router.get("/{news_event_id}", response_model=NewsEventRead)
async def get_news_event(
    news_event_id: UUID,
    service: Annotated[NewsEventService, Depends(get_news_event_service)],
) -> NewsEventRead:
    event = await service.get_event(news_event_id)
    return NewsEventRead.model_validate(event)


@news_events_router.patch(
    "/{news_event_id}",
    response_model=NewsEventRead,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def update_news_event(
    news_event_id: UUID,
    payload: NewsEventUpdate,
    service: Annotated[NewsEventService, Depends(get_news_event_service)],
) -> NewsEventRead:
    event = await service.update_event(news_event_id, payload)
    return NewsEventRead.model_validate(event)


@router.post(
    "/analysis-runs/{analysis_run_id}/correlate-news",
    response_model=NewsCorrelationRunRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def correlate_analysis_run_news(
    analysis_run_id: UUID,
    service: Annotated[NewsCorrelationService, Depends(get_news_correlation_service)],
) -> NewsCorrelationRunRead:
    correlations = await service.correlate_analysis_run_with_news(analysis_run_id, commit=True)
    signal_id = (
        correlations[0].signal_id
        if correlations
        else await service_signal_id(service, analysis_run_id)
    )
    return NewsCorrelationRunRead(
        analysis_run_id=analysis_run_id,
        signal_id=signal_id,
        correlation_count=len(correlations),
        correlations=[NewsCorrelationRead.model_validate(item) for item in correlations],
    )


@router.get(
    "/analysis-runs/{analysis_run_id}/news-correlations",
    response_model=list[NewsCorrelationRead],
)
async def list_analysis_run_news_correlations(
    analysis_run_id: UUID,
    service: Annotated[NewsCorrelationService, Depends(get_news_correlation_service)],
) -> list[NewsCorrelationRead]:
    correlations = await service.list_by_analysis_run_id(analysis_run_id)
    return [NewsCorrelationRead.model_validate(item) for item in correlations]


@router.post(
    "/signals/{signal_id}/correlate-news",
    response_model=NewsCorrelationRunRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def correlate_signal_news(
    signal_id: UUID,
    service: Annotated[NewsCorrelationService, Depends(get_news_correlation_service)],
) -> NewsCorrelationRunRead:
    correlations = await service.correlate_signal_with_news(signal_id, commit=True)
    if correlations:
        analysis_run_id = correlations[0].analysis_run_id
    else:
        signal = await service.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        analysis_run_id = signal.analysis_run_id
    return NewsCorrelationRunRead(
        analysis_run_id=analysis_run_id,
        signal_id=signal_id,
        correlation_count=len(correlations),
        correlations=[NewsCorrelationRead.model_validate(item) for item in correlations],
    )


@router.get("/signals/{signal_id}/news-correlations", response_model=list[NewsCorrelationRead])
async def list_signal_news_correlations(
    signal_id: UUID,
    service: Annotated[NewsCorrelationService, Depends(get_news_correlation_service)],
) -> list[NewsCorrelationRead]:
    correlations = await service.list_by_signal_id(signal_id)
    return [NewsCorrelationRead.model_validate(item) for item in correlations]


async def service_signal_id(service: NewsCorrelationService, analysis_run_id: UUID) -> UUID:
    signal = await service.signal_repository.get_by_analysis_run_id(analysis_run_id)
    if signal is None:
        raise AppError(404, "signal_not_found", "Signal not found")
    return signal.id
