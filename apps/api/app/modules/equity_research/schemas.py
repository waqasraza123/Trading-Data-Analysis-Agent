from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe, normalize_timestamp
from app.modules.equity_research.models import (
    EquityCatalystImportance,
    EquityCatalystSentiment,
    EquityCatalystType,
    EquitySwingCandidateStatus,
    EquitySwingDirectionalBias,
    EquitySwingScanRunStatus,
    EquitySwingSetupQualityLabel,
    EquitySwingSetupType,
    EquityUniverseStatus,
    EquityUniverseType,
)


class EquityUniverseCreate(ApiSchema):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    universe_type: EquityUniverseType = EquityUniverseType.MANUAL
    filters_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "name must not be blank"
            raise ValueError(msg)
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityUniverseUpdate(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    status: EquityUniverseStatus | None = None
    universe_type: EquityUniverseType | None = None
    filters_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            msg = "name must not be blank"
            raise ValueError(msg)
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityUniverseRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: EquityUniverseStatus
    universe_type: EquityUniverseType
    filters_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EquityUniverseMemberCreate(ApiSchema):
    symbol_id: UUID
    ticker: str | None = Field(default=None, max_length=32)
    company_name: str | None = Field(default=None, max_length=160)
    sector: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=160)
    exchange: str | None = Field(default=None, max_length=80)
    market_cap: Decimal | None = Field(default=None, ge=0)
    average_volume: Decimal | None = Field(default=None, ge=0)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @field_validator("company_name", "sector", "industry", "exchange")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityUniverseMembersBulkCreate(ApiSchema):
    members: list[EquityUniverseMemberCreate] = Field(min_length=1, max_length=500)


class EquityUniverseMemberRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    universe_id: UUID
    symbol_id: UUID
    ticker: str
    company_name: str | None
    sector: str | None
    industry: str | None
    exchange: str | None
    market_cap: Decimal | None
    average_volume: Decimal | None
    is_active: bool
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EquitySwingScanFilters(ApiSchema):
    min_average_volume: Decimal | None = Field(default=None, ge=0)
    min_setup_score: Decimal | None = Field(default=None, ge=0, le=1)
    sector: str | None = Field(default=None, max_length=120)
    max_symbols: int | None = Field(default=None, ge=1, le=5000)
    source_id: UUID | None = None

    @field_validator("sector")
    @classmethod
    def normalize_sector(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquitySwingScanOptions(ApiSchema):
    use_existing_analysis_only: bool = True
    generate_setup_context: bool = False
    score_signal_priority: bool = False


class EquitySwingScanCreate(ApiSchema):
    workspace_id: UUID
    universe_id: UUID | None = None
    watchlist_id: UUID | None = None
    scan_profile_key: str = Field(default="continuation_momentum", min_length=1, max_length=80)
    timeframes: list[Timeframe] = Field(default_factory=list, max_length=10)
    filters: EquitySwingScanFilters = Field(default_factory=EquitySwingScanFilters)
    options: EquitySwingScanOptions = Field(default_factory=EquitySwingScanOptions)

    @field_validator("scan_profile_key")
    @classmethod
    def normalize_scan_profile_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            msg = "scan_profile_key must not be blank"
            raise ValueError(msg)
        return normalized

    @model_validator(mode="after")
    def validate_scope(self) -> "EquitySwingScanCreate":
        if self.universe_id is None and self.watchlist_id is None:
            msg = "universe_id or watchlist_id is required"
            raise ValueError(msg)
        if self.universe_id is not None and self.watchlist_id is not None:
            msg = "only one of universe_id or watchlist_id may be provided"
            raise ValueError(msg)
        return self


class EquitySwingScanRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    universe_id: UUID | None
    watchlist_id: UUID | None
    status: EquitySwingScanRunStatus
    scan_version: str
    scan_profile_key: str
    filters_json: dict[str, Any]
    scanned_symbol_count: int
    candidate_count: int
    rejected_count: int
    summary: str
    error_message: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EquitySwingCandidateRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    scan_run_id: UUID
    symbol_id: UUID
    timeframe: str
    candidate_status: EquitySwingCandidateStatus
    setup_type: EquitySwingSetupType
    directional_bias: EquitySwingDirectionalBias
    setup_quality_score: Decimal
    setup_quality_label: EquitySwingSetupQualityLabel
    liquidity_score: Decimal | None
    volume_score: Decimal | None
    trend_quality_score: Decimal | None
    pullback_quality_score: Decimal | None
    relative_strength_score: Decimal | None
    momentum_score: Decimal | None
    volatility_score: Decimal | None
    catalyst_score: Decimal | None
    confidence_context_json: dict[str, Any]
    evidence_json: list[dict[str, Any]]
    risk_notes_json: list[dict[str, Any]]
    setup_context_id: UUID | None
    signal_id: UUID | None
    analysis_run_id: UUID | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EquityCatalystContextCreate(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID
    source_type: str = Field(default="manual", min_length=1, max_length=80)
    event_time: datetime | None = None
    catalyst_type: EquityCatalystType = EquityCatalystType.MANUAL_NOTE
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(min_length=1, max_length=4000)
    importance: EquityCatalystImportance = EquityCatalystImportance.UNKNOWN
    sentiment: EquityCatalystSentiment = EquityCatalystSentiment.UNKNOWN
    raw_reference_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_type", "title", "summary")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "text fields must not be blank"
            raise ValueError(msg)
        return normalized

    @field_validator("event_time")
    @classmethod
    def normalize_event_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_timestamp(value)


class EquityCatalystContextRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    symbol_id: UUID
    source_type: str
    event_time: datetime | None
    catalyst_type: EquityCatalystType
    title: str
    summary: str
    importance: EquityCatalystImportance
    sentiment: EquityCatalystSentiment
    raw_reference_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
