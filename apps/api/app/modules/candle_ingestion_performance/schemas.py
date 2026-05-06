from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candle_ingestion_performance.models import (
    CandleIngestionConflictResolution,
    CandleIngestionConflictType,
    CandleIngestionMode,
    CandleIngestionPerformanceStatus,
)
from app.modules.candles.schemas import NormalizedCandleInput


class CandleIngestionRowOutcome(StrEnum):
    INSERTED = "inserted"
    UPDATED = "updated"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    CONFLICTED = "conflicted"
    FAILED = "failed"


@dataclass(frozen=True)
class CandleIngestionRowReference:
    row_number: int | None
    raw_payload: dict[str, object]


@dataclass(frozen=True)
class CandleIngestionCandidate:
    candle: NormalizedCandleInput
    row_reference: CandleIngestionRowReference


@dataclass
class CandleIngestionCounters:
    rows_received: int = 0
    rows_validated: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped_duplicate: int = 0
    rows_conflicted: int = 0
    rows_failed: int = 0
    batch_count: int = 0

    def add(self, other: "CandleIngestionCounters") -> None:
        self.rows_received += other.rows_received
        self.rows_validated += other.rows_validated
        self.rows_inserted += other.rows_inserted
        self.rows_updated += other.rows_updated
        self.rows_skipped_duplicate += other.rows_skipped_duplicate
        self.rows_conflicted += other.rows_conflicted
        self.rows_failed += other.rows_failed
        self.batch_count += other.batch_count


@dataclass(frozen=True)
class CandleIngestionRowFailure:
    row_reference: CandleIngestionRowReference
    error_code: str
    error_message: str
    conflict_type: CandleIngestionConflictType | None = None


@dataclass(frozen=True)
class CandleIngestionConflictRecord:
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    timestamp: datetime
    conflict_type: CandleIngestionConflictType
    existing_candle_json: dict[str, object]
    incoming_candle_json: dict[str, object]
    resolution: CandleIngestionConflictResolution
    row_reference: CandleIngestionRowReference


@dataclass
class CandleIngestionBatchOutcome:
    counters: CandleIngestionCounters = field(default_factory=CandleIngestionCounters)
    failures: list[CandleIngestionRowFailure] = field(default_factory=list)
    conflicts: list[CandleIngestionConflictRecord] = field(default_factory=list)


class CandleIngestionPerformanceRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    import_batch_id: UUID | None
    provider_polling_request_id: UUID | None
    source_id: UUID | None
    symbol_id: UUID | None
    timeframe: str | None
    status: CandleIngestionPerformanceStatus
    ingestion_mode: CandleIngestionMode
    rows_received: int
    rows_validated: int
    rows_inserted: int
    rows_updated: int
    rows_skipped_duplicate: int
    rows_conflicted: int
    rows_failed: int
    batch_count: int
    elapsed_ms: int | None
    diagnostics_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class CandleIngestionConflictRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    performance_run_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    timestamp: datetime
    conflict_type: CandleIngestionConflictType
    existing_candle_json: dict[str, object]
    incoming_candle_json: dict[str, object]
    resolution: CandleIngestionConflictResolution
    created_at: datetime


class CandleIngestionPerformanceRunListFilters(ApiSchema):
    workspace_id: UUID
    import_batch_id: UUID | None = None
    provider_polling_request_id: UUID | None = None
    source_id: UUID | None = None
    symbol_id: UUID | None = None
    ingestion_mode: CandleIngestionMode | None = None
    status: CandleIngestionPerformanceStatus | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
