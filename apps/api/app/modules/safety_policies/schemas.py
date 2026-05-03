from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SafetyPolicySetStatus(StrEnum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"


class SafetyPolicyEvaluationType(StrEnum):
    TEXT = "text"
    ACTION = "action"
    PAYLOAD = "payload"
    REPORT = "report"
    REASONING_OUTPUT = "reasoning_output"
    WEBHOOK_PAYLOAD = "webhook_payload"
    DATASET_RECORD = "dataset_record"


class SafetyPolicyEvaluationStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class SafetyStatus(StrEnum):
    PASSED = "passed"
    BLOCKED = "blocked"
    REDACTED = "redacted"
    REVIEW_RECOMMENDED = "review_recommended"


class SafetyFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyFinding(BaseModel):
    code: str
    severity: SafetyFindingSeverity
    message: str
    matched_value: str | None = Field(default=None, alias="matchedValue")
    location: str

    model_config = ConfigDict(populate_by_name=True)


class SafetyPolicyRules(BaseModel):
    blocked_trading_actions: list[str] = Field(default_factory=list, alias="blockedTradingActions")
    unsafe_direct_phrases: list[str] = Field(default_factory=list, alias="unsafeDirectPhrases")
    causation_phrases: list[str] = Field(default_factory=list, alias="causationPhrases")
    invented_evidence_phrases: list[str] = Field(default_factory=list, alias="inventedEvidencePhrases")
    secret_keys: list[str] = Field(default_factory=list, alias="secretKeys")
    prohibited_output_claims: list[str] = Field(default_factory=list, alias="prohibitedOutputClaims")
    provider_payload_exposure_keys: list[str] = Field(default_factory=list, alias="providerPayloadExposureKeys")

    model_config = ConfigDict(populate_by_name=True)


class SafetyPolicySetData(BaseModel):
    key: str
    version: str
    status: SafetyPolicySetStatus = SafetyPolicySetStatus.ACTIVE
    description: str
    rules: SafetyPolicyRules


class SafetyPolicySetRead(BaseModel):
    id: str | None = None
    workspace_id: str | None = Field(default=None, alias="workspaceId")
    key: str
    version: str
    status: SafetyPolicySetStatus
    description: str | None = None
    policy_json: dict[str, Any] = Field(alias="policyJson")
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class EvaluateTextRequest(BaseModel):
    workspace_id: str | None = Field(default=None, alias="workspaceId")
    text: str
    source_type: str = Field(default="manual", alias="sourceType")
    source_id: str | None = Field(default=None, alias="sourceId")

    model_config = ConfigDict(populate_by_name=True)


class EvaluateActionRequest(BaseModel):
    workspace_id: str | None = Field(default=None, alias="workspaceId")
    action: str
    source_type: str = Field(default="manual", alias="sourceType")
    source_id: str | None = Field(default=None, alias="sourceId")
    context: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True)


class EvaluatePayloadRequest(BaseModel):
    workspace_id: str | None = Field(default=None, alias="workspaceId")
    payload: dict[str, Any]
    source_type: str = Field(default="manual", alias="sourceType")
    source_id: str | None = Field(default=None, alias="sourceId")
    public_response: bool = Field(default=True, alias="publicResponse")

    model_config = ConfigDict(populate_by_name=True)


class SafetyEvaluationResponse(BaseModel):
    policy_set_key: str = Field(alias="policySetKey")
    policy_set_version: str = Field(alias="policySetVersion")
    evaluation_type: SafetyPolicyEvaluationType = Field(alias="evaluationType")
    status: SafetyPolicyEvaluationStatus
    safety_status: SafetyStatus = Field(alias="safetyStatus")
    findings: list[SafetyFinding] = Field(default_factory=list)
    input_summary_json: dict[str, Any] = Field(default_factory=dict, alias="inputSummaryJson")
    redacted_output_json: dict[str, Any] | list[Any] | str | int | float | bool | None = Field(default=None, alias="redactedOutputJson")

    model_config = ConfigDict(populate_by_name=True)
