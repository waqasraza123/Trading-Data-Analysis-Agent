from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.data_contracts.models import (
    DataContractStatus,
    DataContractValidationStatus,
)


class DataContractRead(ApiReadSchema):
    id: UUID
    key: str
    version: str
    status: DataContractStatus
    description: str
    schema_definition: dict[str, Any] = Field(
        validation_alias="schema_json",
        serialization_alias="schema_json",
    )
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DataContractSeedRead(ApiSchema):
    seeded_count: int
    contract_keys: list[str]


class DataContractValidationRequest(ApiSchema):
    key: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=32)
    payload: dict[str, Any] | list[Any]
    workspace_id: UUID | None = None
    source_type: str | None = Field(default=None, max_length=120)
    source_id: UUID | None = None
    strict: bool = False


class DataContractSourceValidationRequest(ApiSchema):
    source_type: str = Field(min_length=1, max_length=120)
    source_id: UUID
    contract_key: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=32)
    strict: bool = False


class DataContractValidationRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    contract_key: str
    contract_version: str
    source_type: str | None
    source_id: UUID | None
    status: DataContractValidationStatus
    validation_errors_json: list[dict[str, Any]]
    validation_warnings_json: list[dict[str, Any]]
    payload_summary_json: dict[str, Any]
    created_at: datetime


class DataContractValidationResult(ApiSchema):
    contract_key: str
    contract_version: str
    status: DataContractValidationStatus
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    payload_summary: dict[str, Any]
    validation: DataContractValidationRead


class DataContractValidationQuery(ApiSchema):
    workspace_id: UUID | None = None
    contract_key: str | None = Field(default=None, max_length=120)
    contract_version: str | None = Field(default=None, max_length=32)
    source_type: str | None = Field(default=None, max_length=120)
    source_id: UUID | None = None
    status: DataContractValidationStatus | None = None
    limit: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def require_source_type_for_source_id(self) -> "DataContractValidationQuery":
        if self.source_id is not None and self.source_type is None:
            msg = "source_type is required when source_id is provided"
            raise ValueError(msg)
        return self
