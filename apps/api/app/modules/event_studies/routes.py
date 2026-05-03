from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.event_studies.schemas import (
    EventStudyResultRead,
    EventStudyRunRead,
    EventStudyRunRequest,
)
from app.modules.event_studies.service import EventStudyService

router = APIRouter(tags=["event-studies"])


def get_event_study_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> EventStudyService:
    return EventStudyService(session)


@router.post(
    "/event-studies/run",
    response_model=EventStudyRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def run_event_study(
    payload: EventStudyRunRequest,
    service: Annotated[EventStudyService, Depends(get_event_study_service)],
) -> EventStudyRunRead:
    run = await service.run_event_study(payload)
    return EventStudyRunRead.model_validate(run)


@router.get("/event-studies/runs/{run_id}", response_model=EventStudyRunRead)
async def get_event_study_run(
    run_id: UUID,
    service: Annotated[EventStudyService, Depends(get_event_study_service)],
) -> EventStudyRunRead:
    run = await service.get_run(run_id)
    return EventStudyRunRead.model_validate(run)


@router.get("/event-studies/runs/{run_id}/results", response_model=list[EventStudyResultRead])
async def list_event_study_results(
    run_id: UUID,
    service: Annotated[EventStudyService, Depends(get_event_study_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EventStudyResultRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    results = await service.list_results(
        run_id=run_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [EventStudyResultRead.model_validate(result) for result in results]


@router.get("/news-events/{news_event_id}/event-studies", response_model=list[EventStudyRunRead])
async def list_news_event_studies(
    news_event_id: UUID,
    service: Annotated[EventStudyService, Depends(get_event_study_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EventStudyRunRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    runs = await service.list_runs_by_news_event(
        news_event_id=news_event_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [EventStudyRunRead.model_validate(run) for run in runs]
