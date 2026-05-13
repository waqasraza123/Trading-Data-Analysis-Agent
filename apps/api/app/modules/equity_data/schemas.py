from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.equity_data.models import (
    EquityDataOperationStatus,
    EquityDataOperationType,
    EquityDataRequestStatus,
    EquityDataRequestType,
    EquityEarningsImportance,
    EquityEarningsStatus,
)
from app.modules.equity_data.normalizer import normalize_provider, normalize_ticker
from app.modules.job_queue.schemas import JobQueueEventRead, JobQueueJobRead


class EquityDataProviderCapability(ApiSchema):
    provider: str
    label: str
    configured: bool
    external_requests_enabled: bool
    requires_credential_ref: bool
    supports_universe_import: bool
    supports_metadata_lookup: bool
    supports_fundamentals_snapshot: bool
    supports_earnings_calendar: bool
    status: EquityDataRequestStatus
    message: str


class EquityDataProviderTestRequest(ApiSchema):
    workspace_id: UUID
    credential_ref_id: UUID | None = None


class EquityDataProviderTestRead(ApiSchema):
    provider: str
    status: EquityDataRequestStatus
    message: str
    configured: bool


class EquityImportRow(ApiSchema):
    ticker: str = Field(min_length=1, max_length=32)
    company_name: str | None = Field(default=None, alias="companyName", max_length=160)
    exchange: str | None = Field(default=None, max_length=80)
    sector: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=160)
    country: str | None = Field(default=None, max_length=80)
    currency: str | None = Field(default=None, max_length=16)
    market_cap: Decimal | None = Field(default=None, alias="marketCap", ge=0)
    average_volume: Decimal | None = Field(default=None, alias="averageVolume", ge=0)
    shares_float: Decimal | None = Field(default=None, alias="sharesFloat", ge=0)
    is_etf: bool | None = Field(default=None, alias="isEtf")
    is_active: bool = Field(default=True, alias="isActive")
    raw_reference_json: dict[str, Any] = Field(default_factory=dict, alias="rawReferenceJson")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        return normalize_ticker(value)

    @field_validator("company_name", "exchange", "sector", "industry", "country", "currency")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityUniverseImportRowsRequest(ApiSchema):
    workspace_id: UUID = Field(alias="workspaceId")
    universe_id: UUID | None = Field(default=None, alias="universeId")
    create_universe_name: str | None = Field(
        default=None, alias="createUniverseName", max_length=160
    )
    provider: str = "csv_equity_import"
    rows: list[EquityImportRow] = Field(min_length=1, max_length=5000)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        return normalize_provider(value)

    @field_validator("create_universe_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityProviderUniverseImportRequest(ApiSchema):
    workspace_id: UUID = Field(alias="workspaceId")
    provider: str
    credential_ref_id: UUID | None = Field(default=None, alias="credentialRefId")
    universe_id: UUID | None = Field(default=None, alias="universeId")
    create_universe_name: str | None = Field(
        default=None, alias="createUniverseName", max_length=160
    )
    filters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        return normalize_provider(value)

    @field_validator("create_universe_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquitySymbolProviderRequest(ApiSchema):
    workspace_id: UUID = Field(alias="workspaceId")
    provider: str | None = None
    credential_ref_id: UUID | None = Field(default=None, alias="credentialRefId")
    filters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_provider(value)


class EquityEarningsImportRow(ApiSchema):
    symbol_id: UUID | None = Field(default=None, alias="symbolId")
    ticker: str | None = Field(default=None, max_length=32)
    provider: str = "csv_equity_import"
    event_date: date = Field(alias="eventDate")
    fiscal_period: str | None = Field(default=None, alias="fiscalPeriod", max_length=32)
    report_time: str | None = Field(default=None, alias="reportTime", max_length=32)
    eps_estimate: Decimal | None = Field(default=None, alias="epsEstimate")
    eps_actual: Decimal | None = Field(default=None, alias="epsActual")
    revenue_estimate: Decimal | None = Field(default=None, alias="revenueEstimate")
    revenue_actual: Decimal | None = Field(default=None, alias="revenueActual")
    importance: EquityEarningsImportance = EquityEarningsImportance.UNKNOWN
    status: EquityEarningsStatus = EquityEarningsStatus.UNKNOWN
    raw_reference_json: dict[str, Any] = Field(default_factory=dict, alias="rawReferenceJson")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_ticker(value)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        return normalize_provider(value)

    @model_validator(mode="after")
    def validate_symbol_or_ticker(self) -> "EquityEarningsImportRow":
        if self.symbol_id is None and self.ticker is None:
            msg = "symbolId or ticker is required"
            raise ValueError(msg)
        return self


class EquityEarningsImportRowsRequest(ApiSchema):
    workspace_id: UUID = Field(alias="workspaceId")
    provider: str = "csv_equity_import"
    rows: list[EquityEarningsImportRow] = Field(min_length=1, max_length=5000)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        return normalize_provider(value)


class EquityDataProviderRequestRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    provider: str
    request_type: EquityDataRequestType
    status: EquityDataRequestStatus
    credential_ref_id: UUID | None
    universe_id: UUID | None
    symbol_id: UUID | None
    ticker: str | None
    request_json: dict[str, Any]
    response_summary_json: dict[str, Any]
    received_count: int
    stored_count: int
    skipped_count: int
    failed_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EquityDataImportErrorRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    provider_request_id: UUID
    row_number: int | None
    error_code: str
    error_message: str
    raw_item_json: dict[str, Any] | None
    created_at: datetime


class EquitySymbolMetadataSnapshotRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    symbol_id: UUID
    ticker: str
    provider: str
    company_name: str | None
    exchange: str | None
    sector: str | None
    industry: str | None
    country: str | None
    currency: str | None
    market_cap: Decimal | None
    average_volume: Decimal | None
    shares_float: Decimal | None
    is_etf: bool | None
    is_active: bool
    snapshot_time: datetime
    raw_reference_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EquityFundamentalSnapshotRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    symbol_id: UUID
    provider: str
    snapshot_time: datetime
    market_cap: Decimal | None
    average_volume: Decimal | None
    relative_volume: Decimal | None
    beta: Decimal | None
    pe_ratio: Decimal | None
    eps: Decimal | None
    revenue_growth: Decimal | None
    earnings_growth: Decimal | None
    debt_to_equity: Decimal | None
    free_cash_flow: Decimal | None
    raw_reference_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EquityEarningsEventRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    symbol_id: UUID
    provider: str
    event_date: date
    fiscal_period: str | None
    report_time: str | None
    eps_estimate: Decimal | None
    eps_actual: Decimal | None
    revenue_estimate: Decimal | None
    revenue_actual: Decimal | None
    importance: EquityEarningsImportance
    status: EquityEarningsStatus
    raw_reference_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EquityDataOperationRunMode(StrEnum):
    SYNC = "sync"
    QUEUED = "queued"
    AUTO = "auto"


class EquityDataOperationRead(ApiReadSchema):
    id: UUID
    operation_id: UUID = Field(alias="operationId")
    workspace_id: UUID
    operation_type: EquityDataOperationType
    provider_name: str | None
    status: EquityDataOperationStatus
    requested_by_user_id: UUID | None
    idempotency_key: str | None
    progress_current: int
    progress_total: int | None
    progress_message: str | None
    counters_json: dict[str, Any]
    request_summary_json: dict[str, Any]
    result_summary_json: dict[str, Any]
    error_summary_json: dict[str, Any]
    linked_provider_request_id: UUID | None
    linked_job_id: UUID | None
    dry_run: bool
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EquityDataOperationDetailRead(EquityDataOperationRead):
    recent_errors: list[EquityDataImportErrorRead] = Field(
        default_factory=list,
        alias="recentErrors",
    )


class EquityDataOperationDiagnosticItem(ApiSchema):
    source: str
    event_type: str = Field(alias="eventType")
    status: str | None = None
    message: str
    occurred_at: datetime = Field(alias="occurredAt")
    metadata_json: dict[str, Any] = Field(default_factory=dict, alias="metadataJson")


class EquityDataOperationDiagnosticsRead(ApiSchema):
    operation: EquityDataOperationRead
    linked_job: JobQueueJobRead | None = Field(default=None, alias="linkedJob")
    linked_provider_request: EquityDataProviderRequestRead | None = Field(
        default=None,
        alias="linkedProviderRequest",
    )
    job_events: list[JobQueueEventRead] = Field(default_factory=list, alias="jobEvents")
    recent_errors: list[EquityDataImportErrorRead] = Field(
        default_factory=list,
        alias="recentErrors",
    )
    timeline: list[EquityDataOperationDiagnosticItem] = Field(default_factory=list)


class EquityDataOperationListRead(ApiSchema):
    operations: list[EquityDataOperationRead]


class EquityDataOperationSummaryRead(ApiSchema):
    workspace_id: UUID
    total_count: int
    active_count: int
    terminal_count: int
    warning_count: int
    failed_count: int
    cancelled_count: int
    latest_operation_at: datetime | None
    status_counts: dict[str, int]
    operation_type_counts: dict[str, int]
    provider_counts: dict[str, int]
    recent_problem_operations: list[EquityDataOperationRead] = Field(
        default_factory=list,
        alias="recentProblemOperations",
    )


class EquityDataOperationReviewItemRead(ApiSchema):
    operation: EquityDataOperationRead
    review_reason: str = Field(alias="reviewReason")
    recommended_action: str = Field(alias="recommendedAction")
    severity: str
    can_retry: bool = Field(alias="canRetry")
    can_cancel: bool = Field(alias="canCancel")
    stale_after_minutes: int = Field(alias="staleAfterMinutes")
    last_update_at: datetime = Field(alias="lastUpdateAt")


class EquityDataOperationReviewQueueRead(ApiSchema):
    workspace_id: UUID
    stale_after_minutes: int = Field(alias="staleAfterMinutes")
    total_count: int
    retryable_count: int
    cancellable_count: int
    items: list[EquityDataOperationReviewItemRead] = Field(default_factory=list)


class EquityDataOperationLineageNodeRead(ApiSchema):
    operation: EquityDataOperationRead
    relationship: str
    depth: int
    retry_of_operation_id: UUID | None = Field(default=None, alias="retryOfOperationId")
    retry_reason: str | None = Field(default=None, alias="retryReason")
    can_retry: bool = Field(alias="canRetry")
    can_cancel: bool = Field(alias="canCancel")


class EquityDataOperationLineageRead(ApiSchema):
    operation: EquityDataOperationRead
    root_operation: EquityDataOperationRead = Field(alias="rootOperation")
    source_operations: list[EquityDataOperationLineageNodeRead] = Field(
        default_factory=list,
        alias="sourceOperations",
    )
    retry_operations: list[EquityDataOperationLineageNodeRead] = Field(
        default_factory=list,
        alias="retryOperations",
    )
    lineage: list[EquityDataOperationLineageNodeRead] = Field(default_factory=list)
    scanned_count: int = Field(alias="scannedCount")
    scan_limit: int = Field(alias="scanLimit")


class EquityDataOperationCancelRequest(ApiSchema):
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityDataOperationRetryRequest(ApiSchema):
    run_mode: EquityDataOperationRunMode = Field(
        default=EquityDataOperationRunMode.QUEUED,
        alias="runMode",
    )
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=240)
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("idempotency_key", "reason")
    @classmethod
    def normalize_retry_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityOperationUniverseImportRequest(ApiSchema):
    workspace_id: UUID = Field(alias="workspaceId")
    universe_id: UUID | None = Field(default=None, alias="universeId")
    create_universe_name: str | None = Field(
        default=None, alias="createUniverseName", max_length=160
    )
    provider: str = "csv_equity_import"
    rows: list[EquityImportRow] = Field(default_factory=list, max_length=5000)
    filters: dict[str, Any] = Field(default_factory=dict)
    credential_ref_id: UUID | None = Field(default=None, alias="credentialRefId")
    run_mode: EquityDataOperationRunMode = Field(
        default=EquityDataOperationRunMode.AUTO,
        alias="runMode",
    )
    dry_run: bool = Field(default=False, alias="dryRun")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=240)

    @field_validator("provider")
    @classmethod
    def validate_operation_provider(cls, value: str) -> str:
        return normalize_provider(value)

    @field_validator("create_universe_name", "idempotency_key")
    @classmethod
    def normalize_operation_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityEnrichmentOperationRequest(ApiSchema):
    workspace_id: UUID = Field(alias="workspaceId")
    provider: str = "mock_equity_data"
    credential_ref_id: UUID | None = Field(default=None, alias="credentialRefId")
    universe_id: UUID | None = Field(default=None, alias="universeId")
    symbol_ids: list[UUID] = Field(default_factory=list, alias="symbolIds", max_length=1000)
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=100, ge=1, le=1000)
    run_mode: EquityDataOperationRunMode = Field(
        default=EquityDataOperationRunMode.QUEUED,
        alias="runMode",
    )
    dry_run: bool = Field(default=False, alias="dryRun")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=240)

    @field_validator("provider")
    @classmethod
    def validate_enrichment_provider(cls, value: str) -> str:
        return normalize_provider(value)

    @field_validator("idempotency_key")
    @classmethod
    def normalize_enrichment_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityCatalystOperationRequest(ApiSchema):
    workspace_id: UUID = Field(alias="workspaceId")
    universe_id: UUID | None = Field(default=None, alias="universeId")
    symbol_ids: list[UUID] = Field(default_factory=list, alias="symbolIds", max_length=1000)
    limit: int = Field(default=100, ge=1, le=1000)
    run_mode: EquityDataOperationRunMode = Field(
        default=EquityDataOperationRunMode.QUEUED,
        alias="runMode",
    )
    dry_run: bool = Field(default=False, alias="dryRun")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=240)

    @field_validator("idempotency_key")
    @classmethod
    def normalize_catalyst_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class EquityFileImportRead(ApiSchema):
    run_mode: EquityDataOperationRunMode = Field(alias="runMode")
    operation: EquityDataOperationRead | None = None
    provider_request: EquityDataProviderRequestRead | None = Field(
        default=None,
        alias="providerRequest",
    )
    validation_errors: list[EquityDataImportErrorRead] = Field(
        default_factory=list,
        alias="validationErrors",
    )
    rows_received: int = Field(alias="rowsReceived")
    rows_valid: int = Field(alias="rowsValid")
