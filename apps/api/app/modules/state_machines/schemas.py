from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema


class StateTransitionRead(ApiSchema):
    from_state: str = Field(serialization_alias="fromState")
    to_state: str = Field(serialization_alias="toState")
    label: str | None = None


class StateMachineDefinitionRead(ApiReadSchema):
    id: UUID
    key: str
    version: str
    object_type: str
    states_json: list[str]
    transitions_json: list[dict[str, Any]]
    terminal_states_json: list[str]
    metadata_json: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


class StateMachineSeedRead(ApiSchema):
    seeded_count: int
    updated_count: int
    keys: list[str]


class StateTransitionValidationRequest(ApiSchema):
    object_type: str
    from_state: str
    to_state: str
    workspace_id: UUID | None = None
    object_id: UUID | None = None
    state_machine_key: str | None = None
    state_machine_version: str | None = None
    record_validation: bool = True


class StateTransitionValidationRead(ApiSchema):
    state_machine_key: str
    state_machine_version: str
    object_type: str
    object_id: UUID | None = None
    from_state: str
    to_state: str
    validation_status: str
    is_valid: bool
    reason: str
    validation_id: UUID | None = None
    terminal_transition: bool


class StateMachineListFilters(ApiSchema):
    object_type: str | None = None
    status: str | None = None
