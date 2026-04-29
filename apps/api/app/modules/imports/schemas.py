from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.candles.timeframes import Timeframe
from app.modules.imports.models import ImportBatchStatus


class JsonCandleImportRequest(ApiSchema):
    workspace_id: UUID
    user_id: UUID | None = None
    source_id: UUID
    symbol_id: UUID
    timeframe: Timeframe
    candles: list[RawCandlePayload] = Field(min_length=1)


class CsvCandleImportRequest(ApiSchema):
    workspace_id: UUID
    user_id: UUID | None = None
    source_id: UUID
    symbol_id: UUID
    timeframe: Timeframe
    file_name: str | None = None


class ImportBatchRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    user_id: UUID | None
    source_id: UUID
    symbol_id: UUID
    timeframe: str
    file_name: str | None
    file_url: str | None
    status: ImportBatchStatus
    rows_received: int
    rows_valid: int
    rows_invalid: int
    duplicates_skipped: int
    missing_candles_detected: int
    data_quality_score: Decimal | None
    error_summary_json: dict[str, object] | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ImportErrorRead(ApiReadSchema):
    id: UUID
    import_batch_id: UUID
    row_number: int
    error_code: str
    error_message: str
    raw_row_json: dict[str, object]
    created_at: datetime
