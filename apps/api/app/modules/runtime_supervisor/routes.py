from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.runtime_supervisor.models import (
    RuntimeWorkerDefinitionStatus,
    RuntimeWorkerInstanceStatus,
    RuntimeWorkerType,
)
from app.modules.runtime_supervisor.schemas import (
    RuntimeMarkStaleResponse,
    RuntimeRunRequestCreate,
    RuntimeRunRequestRead,
    RuntimeSupervisorHealth,
    RuntimeWorkerDefinitionRead,
    RuntimeWorkerInstanceHeartbeat,
    RuntimeWorkerInstanceRead,
    RuntimeWorkerSeedResponse,
)
from app.modules.runtime_supervisor.service import RuntimeSupervisorService

router = APIRouter(prefix="/runtime-supervisor", tags=["runtime-supervisor"])


def get_runtime_supervisor_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> RuntimeSupervisorService:
    return RuntimeSupervisorService(session)


@router.post("/seed-default-workers", response_model=RuntimeWorkerSeedResponse)
async def seed_default_workers(
    service: Annotated[RuntimeSupervisorService, Depends(get_runtime_supervisor_service)],
) -> RuntimeWorkerSeedResponse:
    result = await service.seed_default_worker_definitions()
    return RuntimeWorkerSeedResponse(
        seeded_count=result.seeded_count,
        updated_count=result.updated_count,
        worker_keys=result.worker_keys,
    )


@router.get("/workers", response_model=list[RuntimeWorkerDefinitionRead])
async def list_workers(
    service: Annotated[RuntimeSupervisorService, Depends(get_runtime_supervisor_service)],
    status_filter: Annotated[RuntimeWorkerDefinitionStatus | None, Query(alias="status")] = None,
    worker_type: RuntimeWorkerType | None = None,
) -> list[RuntimeWorkerDefinitionRead]:
    definitions = await service.list_worker_definitions(
        status=status_filter,
        worker_type=worker_type.value if worker_type is not None else None,
    )
    return [RuntimeWorkerDefinitionRead.model_validate(definition) for definition in definitions]


@router.get("/workers/{worker_key}", response_model=RuntimeWorkerDefinitionRead)
async def get_worker(
    worker_key: str,
    service: Annotated[RuntimeSupervisorService, Depends(get_runtime_supervisor_service)],
) -> RuntimeWorkerDefinitionRead:
    definition = await service.get_worker_definition(worker_key)
    return RuntimeWorkerDefinitionRead.model_validate(definition)


@router.get("/instances", response_model=list[RuntimeWorkerInstanceRead])
async def list_instances(
    service: Annotated[RuntimeSupervisorService, Depends(get_runtime_supervisor_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    worker_definition_key: str | None = None,
    workspace_id: UUID | None = None,
    status_filter: Annotated[RuntimeWorkerInstanceStatus | None, Query(alias="status")] = None,
) -> list[RuntimeWorkerInstanceRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    instances = await service.list_worker_instances(
        limit=pagination.limit,
        offset=pagination.offset,
        worker_definition_key=worker_definition_key,
        workspace_id=workspace_id,
        status=status_filter,
    )
    return [RuntimeWorkerInstanceRead.model_validate(instance) for instance in instances]


@router.post("/instances/heartbeat", response_model=RuntimeWorkerInstanceRead)
async def heartbeat(
    payload: RuntimeWorkerInstanceHeartbeat,
    service: Annotated[RuntimeSupervisorService, Depends(get_runtime_supervisor_service)],
) -> RuntimeWorkerInstanceRead:
    instance = await service.heartbeat(payload)
    return RuntimeWorkerInstanceRead.model_validate(instance)


@router.post("/mark-stale", response_model=RuntimeMarkStaleResponse)
async def mark_stale(
    service: Annotated[RuntimeSupervisorService, Depends(get_runtime_supervisor_service)],
) -> RuntimeMarkStaleResponse:
    instances, stale_before = await service.mark_stale_workers()
    return RuntimeMarkStaleResponse(
        stale_count=len(instances),
        stale_worker_ids=[instance.worker_id for instance in instances],
        stale_before=stale_before,
    )


@router.get("/health", response_model=RuntimeSupervisorHealth)
async def runtime_health(
    service: Annotated[RuntimeSupervisorService, Depends(get_runtime_supervisor_service)],
    workspace_id: UUID | None = None,
) -> RuntimeSupervisorHealth:
    return await service.summarize_runtime_health(workspace_id=workspace_id)


@router.post(
    "/run-requests",
    response_model=RuntimeRunRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_run_request(
    payload: RuntimeRunRequestCreate,
    service: Annotated[RuntimeSupervisorService, Depends(get_runtime_supervisor_service)],
) -> RuntimeRunRequestRead:
    run_request = await service.create_run_request(payload)
    return RuntimeRunRequestRead.model_validate(run_request)


@router.get("/run-requests/{request_id}", response_model=RuntimeRunRequestRead)
async def get_run_request(
    request_id: UUID,
    service: Annotated[RuntimeSupervisorService, Depends(get_runtime_supervisor_service)],
) -> RuntimeRunRequestRead:
    run_request = await service.get_run_request(request_id)
    return RuntimeRunRequestRead.model_validate(run_request)
