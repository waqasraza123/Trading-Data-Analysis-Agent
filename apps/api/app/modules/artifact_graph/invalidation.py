from dataclasses import dataclass
from uuid import UUID

from app.modules.artifact_graph.models import (
    IntelligenceArtifact,
    IntelligenceArtifactDependency,
)
from app.modules.artifact_graph.repository import ArtifactGraphRepository


@dataclass(frozen=True)
class ArtifactPathStep:
    artifact: IntelligenceArtifact
    dependency: IntelligenceArtifactDependency | None


@dataclass(frozen=True)
class ArtifactPath:
    steps: tuple[ArtifactPathStep, ...]

    @property
    def depth(self) -> int:
        return max(len(self.steps) - 1, 0)

    @property
    def terminal_artifact(self) -> IntelligenceArtifact:
        return self.steps[-1].artifact

    def to_path_json(self) -> list[dict[str, object]]:
        serialized: list[dict[str, object]] = []
        for step in self.steps:
            serialized.append(
                {
                    "artifactRecordId": str(step.artifact.id),
                    "artifactType": step.artifact.artifact_type,
                    "artifactId": step.artifact.artifact_id,
                    "artifactKey": step.artifact.artifact_key,
                    "dependencyId": str(step.dependency.id) if step.dependency else None,
                    "relationshipType": (
                        step.dependency.relationship_type if step.dependency else None
                    ),
                }
            )
        return serialized


class ArtifactDependencyTraversal:
    def __init__(self, repository: ArtifactGraphRepository) -> None:
        self.repository = repository

    async def traverse_downstream(
        self,
        root: IntelligenceArtifact,
        max_depth: int,
        max_paths: int,
    ) -> list[ArtifactPath]:
        return await self.traverse(root, max_depth, max_paths, "downstream")

    async def traverse_upstream(
        self,
        root: IntelligenceArtifact,
        max_depth: int,
        max_paths: int,
    ) -> list[ArtifactPath]:
        return await self.traverse(root, max_depth, max_paths, "upstream")

    async def traverse(
        self,
        root: IntelligenceArtifact,
        max_depth: int,
        max_paths: int,
        direction: str,
    ) -> list[ArtifactPath]:
        paths: list[ArtifactPath] = []
        queue: list[tuple[IntelligenceArtifact, tuple[ArtifactPathStep, ...], set[UUID]]] = [
            (root, (ArtifactPathStep(root, None),), {root.id})
        ]
        while queue and len(paths) < max_paths:
            current, current_steps, visited = queue.pop(0)
            if len(current_steps) - 1 >= max_depth:
                continue
            dependencies = (
                await self.repository.list_dependencies_from_sources(
                    current.workspace_id,
                    {current.id},
                )
                if direction == "downstream"
                else await self.repository.list_dependencies_to_targets(
                    current.workspace_id,
                    {current.id},
                )
            )
            next_ids = {
                dependency.target_artifact_record_id
                if direction == "downstream"
                else dependency.source_artifact_record_id
                for dependency in dependencies
            }
            artifacts_by_id = await self.repository.list_artifacts_by_ids(next_ids)
            for dependency in dependencies:
                next_id = (
                    dependency.target_artifact_record_id
                    if direction == "downstream"
                    else dependency.source_artifact_record_id
                )
                if next_id in visited:
                    continue
                next_artifact = artifacts_by_id.get(next_id)
                if next_artifact is None:
                    continue
                next_steps = (
                    *current_steps,
                    ArtifactPathStep(next_artifact, dependency),
                )
                path = ArtifactPath(next_steps)
                paths.append(path)
                if len(paths) >= max_paths:
                    break
                queue.append((next_artifact, next_steps, {*visited, next_id}))
        return paths
