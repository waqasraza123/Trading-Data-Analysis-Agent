from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.analysis.models import AnalysisMode, AnalysisReplayMode, AnalysisRunStatus
from app.modules.candles.timeframes import Timeframe


class AnalysisRunCreate(ApiSchema):
    workspace_id: UUID
    user_id: UUID | None = None
    symbol_id: UUID
    source_id: UUID | None = None
    timeframe: Timeframe
    start_time: datetime
    end_time: datetime
    warmup_start_time: datetime | None = None
    baseline_start_time: datetime | None = None
    analysis_mode: AnalysisMode = AnalysisMode.HISTORICAL
    include_partial_live_candle: bool = False
    include_news_correlation: bool = False
    include_ai_explanation: bool = False

    @model_validator(mode="after")
    def validate_historical_window(self) -> "AnalysisRunCreate":
        if self.start_time > self.end_time:
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        if self.analysis_mode != AnalysisMode.HISTORICAL:
            msg = "POST /analysis-runs only accepts historical analysis_mode"
            raise ValueError(msg)
        return self


class LiveWindowAnalysisRunCreate(ApiSchema):
    workspace_id: UUID
    user_id: UUID | None = None
    symbol_id: UUID
    source_id: UUID | None = None
    timeframe: Timeframe
    lookback_minutes: int = Field(ge=1, le=43200)
    warmup_candles: int | None = Field(default=None, ge=0, le=5000)
    baseline_candles: int | None = Field(default=None, ge=0, le=5000)
    include_partial_live_candle: bool = False
    include_news_correlation: bool = False
    include_ai_explanation: bool = False


class AnalysisRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    user_id: UUID | None
    symbol_id: UUID
    source_id: UUID | None
    replayed_from_analysis_run_id: UUID | None
    replay_mode: AnalysisReplayMode | None
    timeframe: str
    start_time: datetime
    end_time: datetime
    warmup_start_time: datetime | None
    baseline_start_time: datetime | None
    analysis_mode: AnalysisMode
    include_partial_live_candle: bool
    include_news_correlation: bool
    include_ai_explanation: bool
    status: AnalysisRunStatus
    error_code: str | None
    error_message: str | None
    engine_version: str
    rule_set_version: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnalysisReplayRequest(ApiSchema):
    mode: AnalysisReplayMode


class AnalysisReplayRead(ApiSchema):
    original_analysis_run_id: UUID
    replay_analysis_run_id: UUID
    replay_mode: AnalysisReplayMode
    status: AnalysisRunStatus


class AnalysisAuditLogRead(ApiReadSchema):
    id: UUID
    analysis_run_id: UUID
    event_type: str
    message: str
    metadata_json: dict[str, Any] | None
    created_at: datetime
