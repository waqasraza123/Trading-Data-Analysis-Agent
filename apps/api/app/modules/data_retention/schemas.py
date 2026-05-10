from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.data_retention.models import (
    DataRetentionActionType,
    DataRetentionPolicyStatus,
    DataRetentionRunItemStatus,
    DataRetentionRunMode,
    DataRetentionRunStatus,
    DataRetentionTargetType,
)

DEFAULT_RETENTION_POLICY: dict[str, int] = {
    "importBatchRetentionDays": 365,
    "liveEventPayloadRetentionDays": 90,
    "providerPollingPayloadRetentionDays": 90,
    "llmInputRetentionDays": 90,
    "llmOutputRetentionDays": 180,
    "datasetExportRetentionDays": 180,
    "webhookOutboxRetentionDays": 180,
    "chartOcrPayloadRetentionDays": 180,
}


class DataRetentionPolicyDocument(ApiSchema):
    import_batch_retention_days: int = Field(default=365, ge=1, le=3650)
    live_event_payload_retention_days: int = Field(default=90, ge=1, le=3650)
    provider_polling_payload_retention_days: int = Field(default=90, ge=1, le=3650)
    llm_input_retention_days: int = Field(default=90, ge=1, le=3650)
    llm_output_retention_days: int = Field(default=180, ge=1, le=3650)
    dataset_export_retention_days: int = Field(default=180, ge=1, le=3650)
    webhook_outbox_retention_days: int = Field(default=180, ge=1, le=3650)
    chart_ocr_payload_retention_days: int = Field(default=180, ge=1, le=3650)


class DataRetentionPolicyCreate(ApiSchema):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=160)
    status: DataRetentionPolicyStatus = DataRetentionPolicyStatus.ACTIVE
    policy_json: DataRetentionPolicyDocument = Field(default_factory=DataRetentionPolicyDocument)


class DataRetentionPolicyUpdate(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    status: DataRetentionPolicyStatus | None = None
    policy_json: DataRetentionPolicyDocument | None = None


class DataRetentionPolicyRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    name: str
    status: DataRetentionPolicyStatus
    policy_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class DataRetentionRunFilters(ApiSchema):
    workspace_id: UUID
    policy_id: UUID | None = None
    target_types: list[DataRetentionTargetType] | None = None
    older_than: datetime | None = None
    limit_per_target_type: int = Field(default=500, ge=1, le=5000)

    @model_validator(mode="after")
    def validate_target_types(self) -> "DataRetentionRunFilters":
        if self.target_types is not None and len(set(self.target_types)) != len(self.target_types):
            msg = "target_types must not contain duplicates"
            raise ValueError(msg)
        return self


class DataRetentionRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    policy_id: UUID | None
    mode: DataRetentionRunMode
    status: DataRetentionRunStatus
    planned_action_count: int
    applied_action_count: int
    skipped_action_count: int
    failed_action_count: int
    summary: dict[str, object]
    filters_json: dict[str, object]
    result_json: dict[str, object]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DataRetentionRunItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    retention_run_id: UUID
    target_type: DataRetentionTargetType
    target_id: UUID
    action_type: DataRetentionActionType
    status: DataRetentionRunItemStatus
    reason: str
    metadata_json: dict[str, object]
    created_at: datetime
