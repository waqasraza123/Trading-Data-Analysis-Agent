from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.users.models import UserRole


class UserCreate(ApiSchema):
    workspace_id: UUID
    email: str = Field(min_length=3, max_length=320)
    name: str = Field(min_length=1, max_length=160)
    role: UserRole = UserRole.USER

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if "@" not in normalized_value:
            msg = "email must be a valid email address"
            raise ValueError(msg)
        return normalized_value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized_value = value.strip()
        if normalized_value == "":
            msg = "name is required"
            raise ValueError(msg)
        return normalized_value


class UserUpdate(ApiSchema):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    role: UserRole | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = value.strip().lower()
        if "@" not in normalized_value:
            msg = "email must be a valid email address"
            raise ValueError(msg)
        return normalized_value

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


class UserRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    email: str
    name: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
