from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.artifact_graph.invalidation import (
    ArtifactDependencyTraversal,
    ArtifactPath,
)
from app.modules.artifact_graph.models import (
    ArtifactInvalidationEvent,
    ArtifactInvalidationItem,
    ArtifactStatus,
    ArtifactType,
    IntelligenceArtifact,
    IntelligenceArtifactDependency,
)
from app.modules.artifact_graph.repository import ArtifactGraphRepository
from app.modules.artifact_graph.schemas import (
    ArtifactGraphSummaryRead,
    ArtifactInvalidationRequest,
    ArtifactInvalidationResultRead,
    ArtifactRead,
    ArtifactReference,
    ArtifactRegisterRequest,
    ArtifactTraversalRead,
    DependencyLinkRequest,
    DependencyPathRead,
    DependencyRead,
    MarkArtifactCurrentRequest,
)


class ArtifactGraphService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ArtifactGraphRepository(session)
        self.traversal = ArtifactDependencyTraversal(self.repository)

    async def register_artifact(self, payload: ArtifactRegisterRequest) -> ArtifactRead:
        artifact = await self.get_or_create_artifact(
            workspace_id=payload.workspace_id,
            artifact_type=payload.artifact_type,
            artifact_id=payload.artifact_id,
            artifact_key=payload.artifact_key,
            status=payload.status,
            version_label=payload.version_label,
            checksum=payload.checksum,
            metadata_json=payload.metadata_json,
        )
        await self.session.commit()
        return ArtifactRead.model_validate(artifact)

    async def get_or_create_artifact(
        self,
        workspace_id: UUID,
        artifact_type: ArtifactType,
        artifact_id: str,
        artifact_key: str | None = None,
        status: ArtifactStatus = ArtifactStatus.CURRENT,
        version_label: str | None = None,
        checksum: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> IntelligenceArtifact:
        normalized_artifact_id = artifact_id.strip()
        if not normalized_artifact_id:
            raise AppError(422, "artifact_id_required", "Artifact id is required")
        existing = await self.repository.get_artifact_by_source(
            workspace_id=workspace_id,
            artifact_type=artifact_type,
            artifact_id=normalized_artifact_id,
        )
        normalized_metadata = metadata_json or {}
        if existing is not None:
            existing.artifact_key = artifact_key or existing.artifact_key
            existing.status = status
            existing.version_label = version_label
            existing.checksum = checksum
            existing.metadata_json = {**existing.metadata_json, **normalized_metadata}
            return await self.repository.update_artifact(existing)
        return await self.repository.create_artifact(
            IntelligenceArtifact(
                workspace_id=workspace_id,
                artifact_type=artifact_type,
                artifact_id=normalized_artifact_id,
                artifact_key=artifact_key
                or self.build_artifact_key(artifact_type, normalized_artifact_id),
                status=status,
                version_label=version_label,
                checksum=checksum,
                metadata_json=normalized_metadata,
            )
        )

    async def get_artifact(self, artifact_record_id: UUID) -> ArtifactRead:
        artifact = await self.require_artifact(artifact_record_id)
        return ArtifactRead.model_validate(artifact)

    async def get_artifact_by_source(
        self,
        workspace_id: UUID,
        artifact_type: ArtifactType,
        artifact_id: str,
    ) -> ArtifactRead:
        artifact = await self.repository.get_artifact_by_source(
            workspace_id=workspace_id,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
        )
        if artifact is None:
            raise AppError(404, "artifact_not_found", "Artifact not found")
        return ArtifactRead.model_validate(artifact)

    async def link_artifacts(self, payload: DependencyLinkRequest) -> DependencyRead:
        source = await self.resolve_dependency_artifact(
            workspace_id=payload.workspace_id,
            artifact_record_id=payload.source_artifact_record_id,
            artifact_reference=payload.source_artifact,
        )
        target = await self.resolve_dependency_artifact(
            workspace_id=payload.workspace_id,
            artifact_record_id=payload.target_artifact_record_id,
            artifact_reference=payload.target_artifact,
        )
        if (
            source.workspace_id != target.workspace_id
            or source.workspace_id != payload.workspace_id
        ):
            raise AppError(
                422,
                "dependency_workspace_mismatch",
                "Dependency artifacts must belong to the request workspace",
            )
        if source.id == target.id:
            raise AppError(
                422,
                "dependency_self_reference",
                "An artifact cannot depend on itself",
            )
        dependency = await self.repository.create_dependency(
            IntelligenceArtifactDependency(
                workspace_id=payload.workspace_id,
                source_artifact_record_id=source.id,
                target_artifact_record_id=target.id,
                relationship_type=payload.relationship_type,
                dependency_version=payload.dependency_version or self.artifact_graph_version,
                metadata_json=payload.metadata_json,
            )
        )
        await self.session.commit()
        return DependencyRead.model_validate(dependency)

    async def get_upstream_dependencies(
        self,
        artifact_record_id: UUID,
        max_depth: int | None = None,
    ) -> ArtifactTraversalRead:
        root = await self.require_artifact(artifact_record_id)
        paths = await self.traversal.traverse_upstream(
            root=root,
            max_depth=self.resolve_max_depth(max_depth),
            max_paths=self.max_paths,
        )
        return self.to_traversal_read(root, "upstream", self.resolve_max_depth(max_depth), paths)

    async def get_downstream_dependencies(
        self,
        artifact_record_id: UUID,
        max_depth: int | None = None,
    ) -> ArtifactTraversalRead:
        root = await self.require_artifact(artifact_record_id)
        paths = await self.traversal.traverse_downstream(
            root=root,
            max_depth=self.resolve_max_depth(max_depth),
            max_paths=self.max_paths,
        )
        return self.to_traversal_read(root, "downstream", self.resolve_max_depth(max_depth), paths)

    async def get_dependency_path(
        self,
        source_artifact_record_id: UUID,
        target_artifact_record_id: UUID,
        max_depth: int | None = None,
    ) -> DependencyPathRead | None:
        source = await self.require_artifact(source_artifact_record_id)
        await self.require_artifact(target_artifact_record_id)
        paths = await self.traversal.traverse_downstream(
            root=source,
            max_depth=self.resolve_max_depth(max_depth),
            max_paths=self.max_paths,
        )
        for path in paths:
            if path.terminal_artifact.id == target_artifact_record_id:
                return self.to_path_read(path)
        return None

    async def mark_artifact_stale(self, artifact_record_id: UUID) -> ArtifactRead:
        artifact = await self.require_artifact(artifact_record_id)
        artifact.status = ArtifactStatus.STALE
        await self.repository.update_artifact(artifact)
        await self.session.commit()
        return ArtifactRead.model_validate(artifact)

    async def invalidate_downstream(
        self,
        artifact_record_id: UUID,
        payload: ArtifactInvalidationRequest,
    ) -> ArtifactInvalidationResultRead:
        source = await self.require_artifact(artifact_record_id)
        paths = await self.traversal.traverse_downstream(
            root=source,
            max_depth=self.resolve_max_depth(payload.max_depth),
            max_paths=self.max_paths,
        )
        event = await self.repository.create_invalidation_event(
            ArtifactInvalidationEvent(
                workspace_id=source.workspace_id,
                source_artifact_record_id=source.id,
                reason_code=payload.reason_code,
                reason=payload.reason,
                metadata_json={
                    **payload.metadata_json,
                    "artifactGraphVersion": self.artifact_graph_version,
                },
            )
        )
        items: list[ArtifactInvalidationItem] = []
        seen_artifacts: set[UUID] = set()
        for path in paths:
            artifact = path.terminal_artifact
            if artifact.id in seen_artifacts or artifact.id == source.id:
                continue
            seen_artifacts.add(artifact.id)
            previous_status = artifact.status
            artifact.status = ArtifactStatus.STALE
            await self.repository.update_artifact(artifact)
            items.append(
                ArtifactInvalidationItem(
                    workspace_id=artifact.workspace_id,
                    invalidation_event_id=event.id,
                    artifact_record_id=artifact.id,
                    previous_status=previous_status,
                    new_status=ArtifactStatus.STALE,
                    path_json=path.to_path_json(),
                )
            )
        persisted_items = await self.repository.create_invalidation_items(items)
        await self.repository.set_event_invalidated_count(event.id, len(persisted_items))
        await self.session.commit()
        await self.session.refresh(event)
        return ArtifactInvalidationResultRead.model_validate(
            {"event": event, "items": persisted_items}
        )

    async def list_stale_artifacts(
        self,
        workspace_id: UUID,
        artifact_type: ArtifactType | None,
        limit: int,
    ) -> list[ArtifactRead]:
        artifacts = await self.repository.list_stale_artifacts(
            workspace_id=workspace_id,
            artifact_type=artifact_type,
            limit=limit,
        )
        return [ArtifactRead.model_validate(artifact) for artifact in artifacts]

    async def mark_artifact_current(
        self,
        artifact_record_id: UUID,
        payload: MarkArtifactCurrentRequest,
    ) -> ArtifactRead:
        artifact = await self.require_artifact(artifact_record_id)
        artifact.status = ArtifactStatus.CURRENT
        if payload.version_label is not None:
            artifact.version_label = payload.version_label
        if payload.checksum is not None:
            artifact.checksum = payload.checksum
        if payload.metadata_json:
            artifact.metadata_json = {**artifact.metadata_json, **payload.metadata_json}
        await self.repository.update_artifact(artifact)
        await self.session.commit()
        return ArtifactRead.model_validate(artifact)

    async def summarize_artifact_graph(self, workspace_id: UUID) -> ArtifactGraphSummaryRead:
        status_counts = await self.repository.count_artifacts_by_status(workspace_id)
        dependency_count = await self.repository.count_dependencies(workspace_id)
        current_count = status_counts.get(ArtifactStatus.CURRENT, 0)
        stale_count = status_counts.get(ArtifactStatus.STALE, 0)
        artifact_count = sum(status_counts.values())
        return ArtifactGraphSummaryRead(
            workspace_id=workspace_id,
            artifact_count=artifact_count,
            dependency_count=dependency_count,
            stale_count=stale_count,
            current_count=current_count,
            recomputation_candidate_count=stale_count,
        )

    async def require_artifact(self, artifact_record_id: UUID) -> IntelligenceArtifact:
        artifact = await self.repository.get_artifact(artifact_record_id)
        if artifact is None:
            raise AppError(404, "artifact_not_found", "Artifact not found")
        return artifact

    async def resolve_dependency_artifact(
        self,
        workspace_id: UUID,
        artifact_record_id: UUID | None,
        artifact_reference: ArtifactReference | None,
    ) -> IntelligenceArtifact:
        if artifact_record_id is not None:
            artifact = await self.require_artifact(artifact_record_id)
            if artifact.workspace_id != workspace_id:
                raise AppError(
                    422,
                    "dependency_workspace_mismatch",
                    "Dependency artifact belongs to a different workspace",
                )
            return artifact
        if artifact_reference is None:
            raise AppError(422, "artifact_reference_required", "Artifact reference is required")
        return await self.get_or_create_artifact(
            workspace_id=artifact_reference.workspace_id or workspace_id,
            artifact_type=artifact_reference.artifact_type,
            artifact_id=artifact_reference.artifact_id,
            artifact_key=artifact_reference.artifact_key,
            status=artifact_reference.status,
            version_label=artifact_reference.version_label,
            checksum=artifact_reference.checksum,
            metadata_json=artifact_reference.metadata_json,
        )

    def to_traversal_read(
        self,
        root: IntelligenceArtifact,
        direction: str,
        max_depth: int,
        paths: list[ArtifactPath],
    ) -> ArtifactTraversalRead:
        return ArtifactTraversalRead(
            root=ArtifactRead.model_validate(root),
            direction=direction,
            max_depth=max_depth,
            paths=[self.to_path_read(path) for path in paths],
        )

    def to_path_read(self, path: ArtifactPath) -> DependencyPathRead:
        from app.modules.artifact_graph.schemas import DependencyPathStepRead, DependencyRead

        return DependencyPathRead(
            steps=[
                DependencyPathStepRead(
                    artifact=ArtifactRead.model_validate(step.artifact),
                    dependency=(
                        DependencyRead.model_validate(step.dependency)
                        if step.dependency is not None
                        else None
                    ),
                )
                for step in path.steps
            ],
            depth=path.depth,
        )

    def resolve_max_depth(self, max_depth: int | None) -> int:
        if max_depth is None:
            return self.max_traversal_depth
        return min(max_depth, self.max_traversal_depth)

    def build_artifact_key(self, artifact_type: ArtifactType, artifact_id: str) -> str:
        return f"{artifact_type}:{artifact_id}"

    @property
    def artifact_graph_version(self) -> str:
        return self.settings.artifact_graph_version

    @property
    def max_traversal_depth(self) -> int:
        return self.settings.artifact_graph_max_traversal_depth

    @property
    def max_paths(self) -> int:
        return self.settings.artifact_graph_max_paths
