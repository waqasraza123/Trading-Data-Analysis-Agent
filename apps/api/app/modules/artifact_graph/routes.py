from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.artifact_graph.models import ArtifactType
from app.modules.artifact_graph.schemas import (
    ArtifactGraphSummaryRead,
    ArtifactInvalidationRequest,
    ArtifactInvalidationResultRead,
    ArtifactRead,
    ArtifactRegisterRequest,
    ArtifactTraversalRead,
    DependencyLinkRequest,
    DependencyPathRead,
    DependencyRead,
    MarkArtifactCurrentRequest,
)
from app.modules.artifact_graph.service import ArtifactGraphService

router = APIRouter(prefix="/artifact-graph", tags=["artifact-graph"])


def get_artifact_graph_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ArtifactGraphService:
    return ArtifactGraphService(session)


@router.post("/artifacts", response_model=ArtifactRead)
async def register_artifact(
    payload: ArtifactRegisterRequest,
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
) -> ArtifactRead:
    return await service.register_artifact(payload)


@router.get("/artifacts/by-source", response_model=ArtifactRead)
async def get_artifact_by_source(
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
    workspace_id: UUID = Query(alias="workspaceId"),
    artifact_type: ArtifactType = Query(alias="artifactType"),
    artifact_id: str = Query(alias="artifactId"),
) -> ArtifactRead:
    return await service.get_artifact_by_source(workspace_id, artifact_type, artifact_id)


@router.get("/artifacts/{artifact_record_id}", response_model=ArtifactRead)
async def get_artifact(
    artifact_record_id: UUID,
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
) -> ArtifactRead:
    return await service.get_artifact(artifact_record_id)


@router.post("/dependencies", response_model=DependencyRead)
async def link_artifacts(
    payload: DependencyLinkRequest,
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
) -> DependencyRead:
    return await service.link_artifacts(payload)


@router.get(
    "/artifacts/{artifact_record_id}/upstream",
    response_model=ArtifactTraversalRead,
)
async def get_upstream_dependencies(
    artifact_record_id: UUID,
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
    max_depth: int | None = Query(default=None, alias="maxDepth", ge=1),
) -> ArtifactTraversalRead:
    return await service.get_upstream_dependencies(artifact_record_id, max_depth)


@router.get(
    "/artifacts/{artifact_record_id}/downstream",
    response_model=ArtifactTraversalRead,
)
async def get_downstream_dependencies(
    artifact_record_id: UUID,
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
    max_depth: int | None = Query(default=None, alias="maxDepth", ge=1),
) -> ArtifactTraversalRead:
    return await service.get_downstream_dependencies(artifact_record_id, max_depth)


@router.get(
    "/artifacts/{source_artifact_record_id}/dependency-path/{target_artifact_record_id}",
    response_model=DependencyPathRead | None,
)
async def get_dependency_path(
    source_artifact_record_id: UUID,
    target_artifact_record_id: UUID,
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
    max_depth: int | None = Query(default=None, alias="maxDepth", ge=1),
) -> DependencyPathRead | None:
    return await service.get_dependency_path(
        source_artifact_record_id,
        target_artifact_record_id,
        max_depth,
    )


@router.post(
    "/artifacts/{artifact_record_id}/invalidate-downstream",
    response_model=ArtifactInvalidationResultRead,
)
async def invalidate_downstream(
    artifact_record_id: UUID,
    payload: ArtifactInvalidationRequest,
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
) -> ArtifactInvalidationResultRead:
    return await service.invalidate_downstream(artifact_record_id, payload)


@router.get("/stale", response_model=list[ArtifactRead])
async def list_stale_artifacts(
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
    workspace_id: UUID = Query(alias="workspaceId"),
    artifact_type: ArtifactType | None = Query(default=None, alias="artifactType"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[ArtifactRead]:
    return await service.list_stale_artifacts(workspace_id, artifact_type, limit)


@router.post("/artifacts/{artifact_record_id}/mark-current", response_model=ArtifactRead)
async def mark_artifact_current(
    artifact_record_id: UUID,
    payload: MarkArtifactCurrentRequest,
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
) -> ArtifactRead:
    return await service.mark_artifact_current(artifact_record_id, payload)


@router.get("/summary", response_model=ArtifactGraphSummaryRead)
async def summarize_artifact_graph(
    service: Annotated[ArtifactGraphService, Depends(get_artifact_graph_service)],
    workspace_id: UUID = Query(alias="workspaceId"),
) -> ArtifactGraphSummaryRead:
    return await service.summarize_artifact_graph(workspace_id)
