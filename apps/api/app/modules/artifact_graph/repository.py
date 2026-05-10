from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.artifact_graph.models import (
    ArtifactInvalidationEvent,
    ArtifactInvalidationItem,
    ArtifactStatus,
    ArtifactType,
    IntelligenceArtifact,
    IntelligenceArtifactDependency,
)


class ArtifactGraphRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_artifact(self, artifact: IntelligenceArtifact) -> IntelligenceArtifact:
        self.session.add(artifact)
        await self.session.flush()
        await self.session.refresh(artifact)
        return artifact

    async def get_artifact(self, artifact_record_id: UUID) -> IntelligenceArtifact | None:
        return await self.session.get(IntelligenceArtifact, artifact_record_id)

    async def get_artifact_by_source(
        self,
        workspace_id: UUID,
        artifact_type: ArtifactType | str,
        artifact_id: str,
    ) -> IntelligenceArtifact | None:
        statement: Select[tuple[IntelligenceArtifact]] = select(IntelligenceArtifact).where(
            IntelligenceArtifact.workspace_id == workspace_id,
            IntelligenceArtifact.artifact_type == str(artifact_type),
            IntelligenceArtifact.artifact_id == artifact_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_artifact(self, artifact: IntelligenceArtifact) -> IntelligenceArtifact:
        await self.session.flush()
        await self.session.refresh(artifact)
        return artifact

    async def list_stale_artifacts(
        self,
        workspace_id: UUID,
        artifact_type: ArtifactType | None,
        limit: int,
    ) -> list[IntelligenceArtifact]:
        statement: Select[tuple[IntelligenceArtifact]] = (
            select(IntelligenceArtifact)
            .where(
                IntelligenceArtifact.workspace_id == workspace_id,
                IntelligenceArtifact.status == ArtifactStatus.STALE,
            )
            .order_by(IntelligenceArtifact.updated_at.asc())
            .limit(limit)
        )
        if artifact_type is not None:
            statement = statement.where(IntelligenceArtifact.artifact_type == artifact_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_dependency(
        self,
        dependency: IntelligenceArtifactDependency,
    ) -> IntelligenceArtifactDependency:
        existing = await self.get_dependency(
            workspace_id=dependency.workspace_id,
            source_artifact_record_id=dependency.source_artifact_record_id,
            target_artifact_record_id=dependency.target_artifact_record_id,
            relationship_type=dependency.relationship_type,
        )
        if existing is not None:
            existing.dependency_version = dependency.dependency_version
            existing.metadata_json = dependency.metadata_json
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        self.session.add(dependency)
        await self.session.flush()
        await self.session.refresh(dependency)
        return dependency

    async def get_dependency(
        self,
        workspace_id: UUID,
        source_artifact_record_id: UUID,
        target_artifact_record_id: UUID,
        relationship_type: str,
    ) -> IntelligenceArtifactDependency | None:
        statement: Select[tuple[IntelligenceArtifactDependency]] = select(
            IntelligenceArtifactDependency
        ).where(
            IntelligenceArtifactDependency.workspace_id == workspace_id,
            IntelligenceArtifactDependency.source_artifact_record_id == source_artifact_record_id,
            IntelligenceArtifactDependency.target_artifact_record_id == target_artifact_record_id,
            IntelligenceArtifactDependency.relationship_type == relationship_type,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_dependencies_from_sources(
        self,
        workspace_id: UUID,
        source_artifact_record_ids: set[UUID],
    ) -> list[IntelligenceArtifactDependency]:
        if not source_artifact_record_ids:
            return []
        statement: Select[tuple[IntelligenceArtifactDependency]] = select(
            IntelligenceArtifactDependency
        ).where(
            IntelligenceArtifactDependency.workspace_id == workspace_id,
            IntelligenceArtifactDependency.source_artifact_record_id.in_(
                source_artifact_record_ids
            ),
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_dependencies_to_targets(
        self,
        workspace_id: UUID,
        target_artifact_record_ids: set[UUID],
    ) -> list[IntelligenceArtifactDependency]:
        if not target_artifact_record_ids:
            return []
        statement: Select[tuple[IntelligenceArtifactDependency]] = select(
            IntelligenceArtifactDependency
        ).where(
            IntelligenceArtifactDependency.workspace_id == workspace_id,
            IntelligenceArtifactDependency.target_artifact_record_id.in_(
                target_artifact_record_ids
            ),
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_artifacts_by_ids(
        self,
        artifact_record_ids: set[UUID],
    ) -> dict[UUID, IntelligenceArtifact]:
        if not artifact_record_ids:
            return {}
        statement: Select[tuple[IntelligenceArtifact]] = select(IntelligenceArtifact).where(
            IntelligenceArtifact.id.in_(artifact_record_ids)
        )
        result = await self.session.execute(statement)
        return {artifact.id: artifact for artifact in result.scalars().all()}

    async def create_invalidation_event(
        self,
        event: ArtifactInvalidationEvent,
    ) -> ArtifactInvalidationEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def create_invalidation_items(
        self,
        items: list[ArtifactInvalidationItem],
    ) -> list[ArtifactInvalidationItem]:
        if not items:
            return []
        self.session.add_all(items)
        await self.session.flush()
        for item in items:
            await self.session.refresh(item)
        return items

    async def set_event_invalidated_count(
        self,
        event_id: UUID,
        invalidated_count: int,
    ) -> None:
        await self.session.execute(
            update(ArtifactInvalidationEvent)
            .where(ArtifactInvalidationEvent.id == event_id)
            .values(invalidated_count=invalidated_count)
        )
        await self.session.flush()

    async def count_artifacts_by_status(self, workspace_id: UUID) -> dict[str, int]:
        statement = (
            select(IntelligenceArtifact.status, func.count(IntelligenceArtifact.id))
            .where(IntelligenceArtifact.workspace_id == workspace_id)
            .group_by(IntelligenceArtifact.status)
        )
        result = await self.session.execute(statement)
        return {str(status): int(count) for status, count in result.all()}

    async def count_dependencies(self, workspace_id: UUID) -> int:
        statement = select(func.count(IntelligenceArtifactDependency.id)).where(
            IntelligenceArtifactDependency.workspace_id == workspace_id
        )
        result = await self.session.execute(statement)
        return int(result.scalar_one())
