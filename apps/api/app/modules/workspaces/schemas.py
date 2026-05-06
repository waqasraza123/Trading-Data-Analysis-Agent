from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema


class WorkspaceCreate(ApiSchema):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized_value = value.strip()
        if normalized_value == "":
            msg = "name is required"
            raise ValueError(msg)
        return normalized_value


class WorkspaceUpdate(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = value.strip()
        if normalized_value == "":
            msg = "name is required"
            raise ValueError(msg)
        return normalized_value


class WorkspaceRead(ApiReadSchema):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class WorkspaceDefaultUserRead(ApiSchema):
    id: UUID
    role: str
    name: str | None = None


class WorkspaceDefaultContextRead(ApiSchema):
    status: str
    workspace: WorkspaceRead | None = None
    user: WorkspaceDefaultUserRead | None = None
    available_workspaces: list[WorkspaceRead] = Field(default_factory=list)
