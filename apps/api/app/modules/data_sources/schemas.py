from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.data_sources.models import DataSourceStatus, DataSourceType


class DataSourceBase(ApiSchema):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=120)
    source_type: DataSourceType
    provider: str = Field(min_length=1, max_length=64)
    status: DataSourceStatus = DataSourceStatus.ACTIVE
    config_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "provider")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    source_type: DataSourceType | None = None
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    status: DataSourceStatus | None = None
    config_json: dict[str, Any] | None = None

    @field_validator("name", "provider")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class DataSourceRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    name: str
    source_type: DataSourceType
    provider: str
    status: DataSourceStatus
    config_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
