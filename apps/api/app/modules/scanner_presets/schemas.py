from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe
from app.modules.scanner_presets.models import (
    ScannerPresetApplicationStatus,
    ScannerPresetCategory,
    ScannerPresetStatus,
)
from app.modules.symbols.models import MarketType


class ScannerPresetCreate(ApiSchema):
    workspace_id: UUID | None = None
    key: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)
    category: ScannerPresetCategory
    status: ScannerPresetStatus = ScannerPresetStatus.ACTIVE
    preset_version: str = Field(min_length=1, max_length=32)
    market_types_json: list[MarketType] = Field(default_factory=list)
    symbol_templates_json: list[dict[str, Any]] = Field(default_factory=list)
    timeframe_templates_json: list[Timeframe] = Field(default_factory=list)
    session_filters_json: dict[str, Any] = Field(default_factory=dict)
    scan_config_template_json: dict[str, Any] = Field(default_factory=dict)
    watchlist_template_json: dict[str, Any] = Field(default_factory=dict)
    preference_profile_filters_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("key", "name", "description", "preset_version")
    @classmethod
    def normalize_required_string(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "value must not be blank"
            raise ValueError(msg)
        return normalized

    @model_validator(mode="after")
    def dedupe_templates(self) -> "ScannerPresetCreate":
        self.market_types_json = list(dict.fromkeys(self.market_types_json))
        self.timeframe_templates_json = list(dict.fromkeys(self.timeframe_templates_json))
        return self


class ScannerPresetRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    key: str
    name: str
    description: str
    category: ScannerPresetCategory
    status: ScannerPresetStatus
    preset_version: str
    market_types_json: list[str]
    symbol_templates_json: list[dict[str, Any]]
    timeframe_templates_json: list[str]
    session_filters_json: dict[str, Any]
    scan_config_template_json: dict[str, Any]
    watchlist_template_json: dict[str, Any]
    preference_profile_filters_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ScannerPresetApplyRequest(ApiSchema):
    workspace_id: UUID
    symbol_ids: list[UUID] = Field(default_factory=list)
    source_id: UUID | None = None
    preference_profile_id: UUID | None = None
    timeframes: list[Timeframe] = Field(default_factory=list)
    create_watchlist: bool = True
    create_scan_config: bool = True
    name_override: str | None = Field(default=None, max_length=160)

    @field_validator("name_override")
    @classmethod
    def normalize_name_override(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def dedupe_lists(self) -> "ScannerPresetApplyRequest":
        self.symbol_ids = list(dict.fromkeys(self.symbol_ids))
        self.timeframes = list(dict.fromkeys(self.timeframes))
        return self


class ScannerPresetApplicationRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    scanner_preset_id: UUID
    status: ScannerPresetApplicationStatus
    watchlist_id: UUID | None
    scan_config_id: UUID | None
    preference_profile_id: UUID | None
    applied_config_json: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ScannerPresetSeedRead(ApiSchema):
    seeded_count: int
    presets: list[ScannerPresetRead]
