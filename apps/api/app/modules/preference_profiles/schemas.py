from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe
from app.modules.market_sessions.models import MarketSessionLabel
from app.modules.preference_profiles.models import PreferenceProfileStatus
from app.modules.symbols.models import MarketType


class PreferenceProfileCreate(ApiSchema):
    workspace_id: UUID
    user_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    is_default: bool = False
    market_types_json: list[MarketType] = Field(default_factory=list)
    symbol_ids_json: list[UUID] = Field(default_factory=list)
    excluded_symbol_ids_json: list[UUID] = Field(default_factory=list)
    timeframes_json: list[Timeframe] = Field(default_factory=list)
    session_labels_json: list[MarketSessionLabel] = Field(default_factory=list)
    pattern_types_json: list[str] = Field(default_factory=list)
    excluded_pattern_types_json: list[str] = Field(default_factory=list)
    strategy_profile_keys_json: list[str] = Field(default_factory=list)
    minimum_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    minimum_setup_quality: Decimal | None = Field(default=None, ge=0, le=1)
    max_stale_seconds: int | None = Field(default=None, gt=0)
    require_fresh_data: bool = False
    require_timeframe_agreement: bool = False
    require_acceptable_data_quality: bool = False
    include_news_context: bool = False
    include_outcomes: bool = False
    notification_preferences_json: dict[str, Any] = Field(default_factory=dict)
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

    @field_validator(
        "pattern_types_json",
        "excluded_pattern_types_json",
        "strategy_profile_keys_json",
    )
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        return dedupe_strings(value)

    @model_validator(mode="after")
    def normalize_lists(self) -> "PreferenceProfileCreate":
        self.market_types_json = list(dict.fromkeys(self.market_types_json))
        self.symbol_ids_json = list(dict.fromkeys(self.symbol_ids_json))
        self.excluded_symbol_ids_json = list(dict.fromkeys(self.excluded_symbol_ids_json))
        self.timeframes_json = list(dict.fromkeys(self.timeframes_json))
        self.session_labels_json = list(dict.fromkeys(self.session_labels_json))
        return self


class PreferenceProfileUpdate(ApiSchema):
    user_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    status: PreferenceProfileStatus | None = None
    is_default: bool | None = None
    market_types_json: list[MarketType] | None = None
    symbol_ids_json: list[UUID] | None = None
    excluded_symbol_ids_json: list[UUID] | None = None
    timeframes_json: list[Timeframe] | None = None
    session_labels_json: list[MarketSessionLabel] | None = None
    pattern_types_json: list[str] | None = None
    excluded_pattern_types_json: list[str] | None = None
    strategy_profile_keys_json: list[str] | None = None
    minimum_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    minimum_setup_quality: Decimal | None = Field(default=None, ge=0, le=1)
    max_stale_seconds: int | None = Field(default=None, gt=0)
    require_fresh_data: bool | None = None
    require_timeframe_agreement: bool | None = None
    require_acceptable_data_quality: bool | None = None
    include_news_context: bool | None = None
    include_outcomes: bool | None = None
    notification_preferences_json: dict[str, Any] | None = None
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

    @field_validator(
        "pattern_types_json",
        "excluded_pattern_types_json",
        "strategy_profile_keys_json",
    )
    @classmethod
    def normalize_string_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return dedupe_strings(value)

    @field_validator(
        "market_types_json",
        "symbol_ids_json",
        "excluded_symbol_ids_json",
        "timeframes_json",
        "session_labels_json",
    )
    @classmethod
    def dedupe_optional_list(cls, value: list[Any] | None) -> list[Any] | None:
        if value is None:
            return None
        return list(dict.fromkeys(value))


class PreferenceProfileRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    user_id: UUID | None
    name: str
    description: str | None
    status: PreferenceProfileStatus
    is_default: bool
    market_types_json: list[str]
    symbol_ids_json: list[str]
    excluded_symbol_ids_json: list[str]
    timeframes_json: list[str]
    session_labels_json: list[str]
    pattern_types_json: list[str]
    excluded_pattern_types_json: list[str]
    strategy_profile_keys_json: list[str]
    minimum_confidence: Decimal | None
    minimum_setup_quality: Decimal | None
    max_stale_seconds: int | None
    require_fresh_data: bool
    require_timeframe_agreement: bool
    require_acceptable_data_quality: bool
    include_news_context: bool
    include_outcomes: bool
    notification_preferences_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PreferenceProfileMatchRead(ApiSchema):
    profile_id: UUID
    signal_id: UUID
    matches: bool
    included_reasons: list[str]
    excluded_reasons: list[str]
    preference_warnings: list[str]


class PreferenceProfileFilterContextRead(ApiSchema):
    profile: PreferenceProfileRead
    filters: dict[str, Any]
    safety_boundaries: list[str]


def dedupe_strings(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        item = value.strip()
        if item:
            normalized.append(item)
    return list(dict.fromkeys(normalized))
