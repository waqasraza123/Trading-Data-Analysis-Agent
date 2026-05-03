from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.rule_packs.models import ReplaySupportStatus, RulePackStatus


class RulePackCreate(ApiSchema):
    workspace_id: UUID | None = None
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=64)
    status: RulePackStatus = RulePackStatus.DRAFT
    description: str | None = Field(default=None, max_length=1000)
    engine_versions_json: dict[str, Any] = Field(default_factory=dict)
    strategy_profile_refs_json: dict[str, Any] = Field(default_factory=dict)
    parser_versions_json: dict[str, Any] = Field(default_factory=dict)
    threshold_config_json: dict[str, Any] = Field(default_factory=dict)
    module_versions_json: dict[str, Any] = Field(default_factory=dict)
    compatibility_json: dict[str, Any] = Field(default_factory=dict)


class RulePackSeedRequest(ApiSchema):
    workspace_id: UUID | None = None


class RulePackRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    key: str
    name: str
    version: str
    status: RulePackStatus
    description: str | None
    engine_versions_json: dict[str, Any]
    strategy_profile_refs_json: dict[str, Any]
    parser_versions_json: dict[str, Any]
    threshold_config_json: dict[str, Any]
    module_versions_json: dict[str, Any]
    compatibility_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ReproducibilityManifestGenerateRequest(ApiSchema):
    force_recompute: bool = False


class ReproducibilityManifestRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID
    signal_id: UUID | None
    rule_pack_id: UUID | None
    manifest_version: str
    engine_snapshot_json: dict[str, Any]
    strategy_profile_snapshot_json: dict[str, Any]
    parser_snapshot_json: dict[str, Any]
    module_snapshot_json: dict[str, Any]
    data_source_snapshot_json: dict[str, Any]
    candle_policy_snapshot_json: dict[str, Any]
    replay_support_status: ReplaySupportStatus
    summary: str
    created_at: datetime
    updated_at: datetime
