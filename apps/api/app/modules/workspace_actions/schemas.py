from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema


class WorkspaceQuickActionRequest(ApiSchema):
    action_type: str = Field(min_length=1, max_length=80)
    watchlist_id: UUID | None = None
    preference_profile_id: UUID | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class WorkspaceQuickActionResponse(ApiReadSchema):
    workspace_id: UUID
    action_type: str
    status: str
    summary: str
    created_artifact_ids_json: dict[str, Any] = Field(default_factory=dict)
    result_json: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
