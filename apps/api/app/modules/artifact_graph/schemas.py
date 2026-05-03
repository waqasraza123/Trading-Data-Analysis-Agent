from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.artifact_graph.models import (
    ArtifactInvalidationReasonCode,
    ArtifactRelationshipType,
    ArtifactStatus,
    ArtifactType,
)


class ArtifactReference(ApiSchema):
    workspace_id: UUID | None = None
    artifact_type: ArtifactType
    artifact_id: str = Field(min_length=1, max_length=128)
    artifact_key: str | None = Field(default=None, max_length=255)
    status: ArtifactStatus = ArtifactStatus.CURRENT
    version_label: str | None = Field(default=None, max_length=80)
    checksum: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] = Field(default_factory=dict, alias="metadata")


class ArtifactRegisterRequest(ApiSchema):
    workspace_id: UUID
    artifact_type: ArtifactType
    artifact_id: str = Field(min_length=1, max_length=128)
    artifact_key: str | None = Field(default=None, max_length=255)
    status: ArtifactStatus = ArtifactStatus.CURRENT
    version_label: str | None = Field(default=None, max_length=80)
    checksum: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] = Field(default_factory=dict, alias="metadata")


class DependencyLinkRequest(ApiSchema):
    workspace_id: UUID
    source_artifact_record_id: UUID | None = None
    target_artifact_record_id: UUID | None = None
    source_artifact: ArtifactReference | None = None
    target_artifact: ArtifactReference | None = None
    relationship_type: ArtifactRelationshipType
    dependency_version: str | None = Field(default=None, max_length=32)
    metadata_json: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    @model_validator(mode="after")
    def validate_artifact_references(self) -> "DependencyLinkRequest":
        if self.source_artifact_record_id is None and self.source_artifact is None:
            msg = "source_artifact_record_id or source_artifact is required"
            raise ValueError(msg)
        if self.target_artifact_record_id is None and self.target_artifact is None:
            msg = "target_artifact_record_id or target_artifact is required"
            raise ValueError(msg)
        return self


class ArtifactInvalidationRequest(ApiSchema):
    reason_code: ArtifactInvalidationReasonCode = ArtifactInvalidationReasonCode.MANUAL_INVALIDATION
    reason: str = Field(min_length=1, max_length=1000)
    metadata_json: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    max_depth: int | None = Field(default=None, ge=1, le=64)


class MarkArtifactCurrentRequest(ApiSchema):
    version_label: str | None = Field(default=None, max_length=80)
    checksum: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] = Field(default_factory=dict, alias="metadata")


class ArtifactRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    artifact_type: ArtifactType
    artifact_id: str
    artifact_key: str
    status: ArtifactStatus
    version_label: str | None
    checksum: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DependencyRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    source_artifact_record_id: UUID
    target_artifact_record_id: UUID
    relationship_type: ArtifactRelationshipType
    dependency_version: str
    metadata_json: dict[str, Any]
    created_at: datetime


class DependencyEdgeRead(ApiSchema):
    dependency: DependencyRead
    source_artifact: ArtifactRead
    target_artifact: ArtifactRead


class DependencyPathStepRead(ApiSchema):
    artifact: ArtifactRead
    dependency: DependencyRead | None = None


class DependencyPathRead(ApiSchema):
    steps: list[DependencyPathStepRead]
    depth: int


class ArtifactTraversalRead(ApiSchema):
    root: ArtifactRead
    direction: str
    max_depth: int
    paths: list[DependencyPathRead]


class ArtifactInvalidationItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    invalidation_event_id: UUID
    artifact_record_id: UUID
    previous_status: ArtifactStatus
    new_status: ArtifactStatus
    path_json: list[dict[str, Any]]
    created_at: datetime


class ArtifactInvalidationEventRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    source_artifact_record_id: UUID
    reason_code: ArtifactInvalidationReasonCode
    reason: str
    invalidated_count: int
    metadata_json: dict[str, Any]
    created_at: datetime


class ArtifactInvalidationResultRead(ApiSchema):
    event: ArtifactInvalidationEventRead
    items: list[ArtifactInvalidationItemRead]


class ArtifactGraphSummaryRead(ApiSchema):
    workspace_id: UUID
    artifact_count: int
    dependency_count: int
    stale_count: int
    current_count: int
    recomputation_candidate_count: int
