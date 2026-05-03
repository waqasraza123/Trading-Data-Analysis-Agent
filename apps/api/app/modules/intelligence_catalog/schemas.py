from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.intelligence_catalog.models import IntelligenceCatalogArtifactType


class IntelligenceCatalogIndexRequest(ApiSchema):
    artifact_type: IntelligenceCatalogArtifactType
    artifact_id: UUID


class IntelligenceCatalogRemoveRequest(ApiSchema):
    workspace_id: UUID
    artifact_type: IntelligenceCatalogArtifactType
    artifact_id: UUID


class IntelligenceCatalogReindexRequest(ApiSchema):
    workspace_id: UUID
    artifact_types: list[IntelligenceCatalogArtifactType] | None = None
    limit: int = Field(default=1000, ge=1, le=5000)


class IntelligenceCatalogSearchQuery(ApiSchema):
    workspace_id: UUID
    query: str | None = None
    artifact_types: list[IntelligenceCatalogArtifactType] | None = None
    status: str | None = None
    symbol_id: UUID | None = None
    timeframe: str | None = None
    strategy_profile_key: str | None = None
    pattern_type: str | None = None
    bias: str | None = None
    outcome_label: str | None = None
    source_type: str | None = None
    tags: list[str] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_time_window(self) -> "IntelligenceCatalogSearchQuery":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        if self.query is not None:
            normalized_query = " ".join(self.query.split())
            self.query = normalized_query or None
        if self.tags is not None:
            self.tags = sorted({tag.strip() for tag in self.tags if tag.strip()})
        return self


class IntelligenceCatalogUpsert(ApiSchema):
    workspace_id: UUID
    artifact_type: IntelligenceCatalogArtifactType
    artifact_id: UUID
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=4000)
    status: str | None = Field(default=None, max_length=64)
    symbol_id: UUID | None = None
    timeframe: str | None = Field(default=None, max_length=16)
    strategy_profile_key: str | None = Field(default=None, max_length=80)
    pattern_type: str | None = Field(default=None, max_length=80)
    bias: str | None = Field(default=None, max_length=32)
    classification_status: str | None = Field(default=None, max_length=64)
    quality_label: str | None = Field(default=None, max_length=64)
    readiness_label: str | None = Field(default=None, max_length=64)
    outcome_label: str | None = Field(default=None, max_length=64)
    source_type: str | None = Field(default=None, max_length=64)
    tags_json: list[str] = Field(default_factory=list)
    searchable_text: str = Field(min_length=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    artifact_created_at: datetime | None = None

    @model_validator(mode="after")
    def normalize_catalog_payload(self) -> "IntelligenceCatalogUpsert":
        self.tags_json = sorted({tag.strip() for tag in self.tags_json if tag.strip()})
        self.searchable_text = " ".join(self.searchable_text.split())
        return self


class IntelligenceCatalogItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    artifact_type: IntelligenceCatalogArtifactType
    artifact_id: UUID
    title: str
    summary: str
    status: str | None
    symbol_id: UUID | None
    timeframe: str | None
    strategy_profile_key: str | None
    pattern_type: str | None
    bias: str | None
    classification_status: str | None
    quality_label: str | None
    readiness_label: str | None
    outcome_label: str | None
    source_type: str | None
    tags_json: list[str]
    metadata_json: dict[str, Any]
    artifact_created_at: datetime | None
    indexed_at: datetime
    created_at: datetime
    updated_at: datetime


class IntelligenceCatalogSearchRead(ApiSchema):
    items: list[IntelligenceCatalogItemRead]
    limit: int
    offset: int


class IntelligenceCatalogReindexRead(ApiSchema):
    workspace_id: UUID
    indexed_count: int
    skipped_count: int
    artifact_types: list[IntelligenceCatalogArtifactType]
