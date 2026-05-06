from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.job_queue.models import (
    JobQueueDefinitionStatus,
    JobQueueItemStatus,
    JobQueueJobType,
)
from app.modules.job_queue.schemas import (
    JobQueueCancelRequest,
    JobQueueDefinitionRead,
    JobQueueEventRead,
    JobQueueJobCreate,
    JobQueueJobRead,
    JobQueueSeedDefinitionsResponse,
)
from app.modules.job_queue.service import JobQueueService

router = APIRouter(prefix="/job-queue", tags=["job-queue"])


def get_job_queue_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JobQueueService:
    return JobQueueService(session)


@router.post("/jobs", response_model=JobQueueJobRead, status_code=status.HTTP_201_CREATED)
async def enqueue_job(
    payload: JobQueueJobCreate,
    service: Annotated[JobQueueService, Depends(get_job_queue_service)],
) -> JobQueueJobRead:
    job = await service.enqueue_job(payload)
    return JobQueueJobRead.model_validate(job)


@router.get("/jobs", response_model=list[JobQueueJobRead])
async def list_jobs(
    service: Annotated[JobQueueService, Depends(get_job_queue_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: Annotated[UUID | None, Query(alias="workspaceId")] = None,
    queue_name: Annotated[str | None, Query(alias="queueName")] = None,
    job_type: Annotated[JobQueueJobType | None, Query(alias="jobType")] = None,
    status_filter: Annotated[JobQueueItemStatus | None, Query(alias="status")] = None,
) -> list[JobQueueJobRead]:
    jobs = await service.list_jobs(
        limit=limit,
        offset=offset,
        workspace_id=workspace_id,
        queue_name=queue_name,
        job_type=job_type,
        status=status_filter,
    )
    return [JobQueueJobRead.model_validate(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=JobQueueJobRead)
async def get_job(
    job_id: UUID,
    service: Annotated[JobQueueService, Depends(get_job_queue_service)],
) -> JobQueueJobRead:
    job = await service.get_job(job_id)
    return JobQueueJobRead.model_validate(job)


@router.post("/jobs/{job_id}/cancel", response_model=JobQueueJobRead)
async def cancel_job(
    job_id: UUID,
    payload: JobQueueCancelRequest,
    service: Annotated[JobQueueService, Depends(get_job_queue_service)],
) -> JobQueueJobRead:
    job = await service.cancel_job(job_id, reason=payload.reason)
    return JobQueueJobRead.model_validate(job)


@router.get("/jobs/{job_id}/events", response_model=list[JobQueueEventRead])
async def list_job_events(
    job_id: UUID,
    service: Annotated[JobQueueService, Depends(get_job_queue_service)],
) -> list[JobQueueEventRead]:
    events = await service.list_events(job_id)
    return [JobQueueEventRead.model_validate(event) for event in events]


@router.post(
    "/definitions/seed-default",
    response_model=JobQueueSeedDefinitionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def seed_default_definitions(
    service: Annotated[JobQueueService, Depends(get_job_queue_service)],
) -> JobQueueSeedDefinitionsResponse:
    result = await service.seed_default_job_definitions()
    return JobQueueSeedDefinitionsResponse(
        seeded_count=result.seeded_count,
        updated_count=result.updated_count,
        definition_keys=result.definition_keys,
    )


@router.get("/definitions", response_model=list[JobQueueDefinitionRead])
async def list_definitions(
    service: Annotated[JobQueueService, Depends(get_job_queue_service)],
    status_filter: Annotated[JobQueueDefinitionStatus | None, Query(alias="status")] = None,
    queue_name: Annotated[str | None, Query(alias="queueName")] = None,
    job_type: Annotated[JobQueueJobType | None, Query(alias="jobType")] = None,
) -> list[JobQueueDefinitionRead]:
    definitions = await service.list_definitions(
        status=status_filter,
        queue_name=queue_name,
        job_type=job_type,
    )
    return [JobQueueDefinitionRead.model_validate(definition) for definition in definitions]
