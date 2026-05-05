from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe
from app.modules.data_sources.models import DataSourceType
from app.modules.provider_credentials.models import ProviderCredentialType
from app.modules.symbols.models import MarketType
from app.modules.users.models import UserRole
from app.modules.workspace_setup.steps import (
    WorkspaceSetupStatus,
    WorkspaceSetupStepKey,
    WorkspaceSetupStepStatus,
)


class WorkspaceSetupStartRequest(ApiSchema):
    workspace_id: UUID | None = None
    user_id: UUID | None = None
    initial_context_json: dict[str, Any] = Field(default_factory=dict)


class WorkspaceStepInput(ApiSchema):
    mode: Literal["create", "select"] = "create"
    workspace_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_mode(self) -> "WorkspaceStepInput":
        if self.mode == "select" and self.workspace_id is None:
            raise ValueError("workspace_id is required when selecting a workspace")
        if self.mode == "create" and self.name is None:
            raise ValueError("name is required when creating a workspace")
        return self


class UserStepInput(ApiSchema):
    mode: Literal["create", "select"] = "create"
    user_id: UUID | None = None
    email: str | None = Field(default=None, min_length=3, max_length=320)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    role: UserRole = UserRole.ANALYST

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("email must be a valid email address")
        return normalized

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_mode(self) -> "UserStepInput":
        if self.mode == "select" and self.user_id is None:
            raise ValueError("user_id is required when selecting a user")
        if self.mode == "create" and (self.email is None or self.name is None):
            raise ValueError("email and name are required when creating a user")
        return self


class SymbolsStepInput(ApiSchema):
    market_type: MarketType
    symbol_ids: list[UUID] = Field(default_factory=list)
    symbol_codes: list[str] = Field(default_factory=list)
    create_missing_symbols: bool = False

    @field_validator("symbol_codes")
    @classmethod
    def normalize_symbol_codes(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_selection(self) -> "SymbolsStepInput":
        self.symbol_ids = list(dict.fromkeys(self.symbol_ids))
        if not self.symbol_ids and not self.symbol_codes:
            raise ValueError("at least one symbol is required")
        return self


class DataSourceStepInput(ApiSchema):
    mode: Literal["create", "select"] = "create"
    data_source_id: UUID | None = None
    source_type: DataSourceType | Literal["csv", "json", "mock", "provider", "live"] = (
        DataSourceType.MANUAL_SEED
    )
    name: str | None = Field(default=None, min_length=1, max_length=120)
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    config_json: dict[str, Any] = Field(default_factory=dict)
    credential_ref_id: UUID | None = None

    @field_validator("name", "provider")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_mode(self) -> "DataSourceStepInput":
        if self.mode == "select" and self.data_source_id is None:
            raise ValueError("data_source_id is required when selecting a data source")
        return self


class CredentialReferenceStepInput(ApiSchema):
    mode: Literal["none", "create", "select"] = "none"
    credential_ref_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    credential_type: ProviderCredentialType = ProviderCredentialType.NONE_REQUIRED
    secret_ref: str | None = Field(default=None, min_length=1, max_length=255)
    public_metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "provider", "secret_ref")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WatchlistStepInput(ApiSchema):
    mode: Literal["create", "select"] = "create"
    watchlist_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    symbol_ids: list[UUID] = Field(default_factory=list)
    timeframes: list[Timeframe] = Field(default_factory=list)
    source_id: UUID | None = None

    @model_validator(mode="after")
    def validate_mode(self) -> "WatchlistStepInput":
        self.symbol_ids = list(dict.fromkeys(self.symbol_ids))
        self.timeframes = list(dict.fromkeys(self.timeframes))
        if self.mode == "select" and self.watchlist_id is None:
            raise ValueError("watchlist_id is required when selecting a watchlist")
        if self.mode == "create" and (not self.name or not self.symbol_ids or not self.timeframes):
            raise ValueError("name, symbol_ids, and timeframes are required")
        return self


class ScannerPresetStepInput(ApiSchema):
    preset_id: UUID | None = None
    preset_key: str | None = Field(default=None, min_length=1, max_length=96)
    symbol_ids: list[UUID] = Field(default_factory=list)
    source_id: UUID | None = None
    preference_profile_id: UUID | None = None
    timeframes: list[Timeframe] = Field(default_factory=list)
    create_watchlist: bool = True
    create_scan_config: bool = True
    name_override: str | None = Field(default=None, max_length=160)


class PreferenceProfileStepInput(ApiSchema):
    mode: Literal["create", "select"] = "create"
    preference_profile_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    user_id: UUID | None = None
    market_types: list[MarketType] = Field(default_factory=list)
    symbol_ids: list[UUID] = Field(default_factory=list)
    timeframes: list[Timeframe] = Field(default_factory=list)
    require_fresh_data: bool = True
    require_timeframe_agreement: bool = False
    require_acceptable_data_quality: bool = True
    minimum_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    minimum_setup_quality: Decimal | None = Field(default=None, ge=0, le=1)
    is_default: bool = True


class DemoDataStepInput(ApiSchema):
    enabled: bool = False
    symbol_ids: list[UUID] = Field(default_factory=list)
    source_id: UUID | None = None
    timeframes: list[Timeframe] = Field(default_factory=list)
    candle_count: int = Field(default=160, ge=40, le=2000)
    pattern: str = "crypto_tick_sample"


class ReadinessCheckStepInput(ApiSchema):
    run: bool = True


class FirstScanStepInput(ApiSchema):
    run: bool = False
    scan_config_id: UUID | None = None


WorkspaceSetupStepInput = (
    WorkspaceStepInput
    | UserStepInput
    | SymbolsStepInput
    | DataSourceStepInput
    | CredentialReferenceStepInput
    | WatchlistStepInput
    | ScannerPresetStepInput
    | PreferenceProfileStepInput
    | DemoDataStepInput
    | ReadinessCheckStepInput
    | FirstScanStepInput
)


class WorkspaceSetupStepRequest(ApiSchema):
    input: dict[str, Any] = Field(default_factory=dict)


class WorkspaceSetupStepResultRead(ApiReadSchema):
    id: UUID
    setup_run_id: UUID
    step_key: WorkspaceSetupStepKey
    status: WorkspaceSetupStepStatus
    input_json: dict[str, Any]
    output_json: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class WorkspaceSetupRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    user_id: UUID | None
    status: WorkspaceSetupStatus
    setup_version: str
    current_step: WorkspaceSetupStepKey
    completed_steps_json: list[str]
    skipped_steps_json: list[str]
    failed_steps_json: list[str]
    result_json: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    step_results: list[WorkspaceSetupStepResultRead] = Field(default_factory=list)


class WorkspaceSetupDemoWorkspaceRequest(ApiSchema):
    workspace_name: str = Field(default="Demo Market Workspace", min_length=1, max_length=120)
    operator_email: str = Field(default="operator@example.test", min_length=3, max_length=320)
    operator_name: str = Field(default="Demo Operator", min_length=1, max_length=160)
    market_type: MarketType = MarketType.CRYPTO
    symbol_codes: list[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    timeframes: list[Timeframe] = Field(default_factory=lambda: [Timeframe.ONE_MINUTE])
    seed_demo_data: bool = True


class WorkspaceSetupDemoWorkspaceResponse(ApiSchema):
    setup_run: WorkspaceSetupRunRead
    workspace_id: UUID | None
    user_id: UUID | None
    watchlist_id: UUID | None
    scan_config_id: UUID | None
    readiness_run_id: UUID | None
