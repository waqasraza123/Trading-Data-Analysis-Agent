from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ChartScreenshotRunStatus(StrEnum):
    RECEIVED = "received"
    PARSING = "parsing"
    INGESTED = "ingested"
    REVIEW_REQUIRED = "review_required"
    ANALYSIS_TRIGGERED = "analysis_triggered"
    ANALYSIS_FAILED = "analysis_failed"
    FAILED = "failed"
    COMPLETED = "completed"


class ChartTrendDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNCLEAR = "unclear"
    UNKNOWN = "unknown"


class ChartScreenshotRun(Base):
    __tablename__ = "chart_screenshot_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('received', 'parsing', 'ingested', 'review_required', "
            "'analysis_triggered', 'analysis_failed', 'failed', 'completed')",
            name="chart_screenshot_runs_status_allowed",
        ),
        CheckConstraint(
            "analysis_hypothesis in ('bullish', 'bearish', 'neutral', 'unclear', 'unknown')",
            name="chart_screenshot_runs_analysis_hypothesis_allowed",
        ),
        CheckConstraint(
            "extraction_confidence >= 0 and extraction_confidence <= 1",
            name="chart_screenshot_runs_extraction_confidence_range",
        ),
        CheckConstraint(
            "analysis_hypothesis_confidence is null or (analysis_hypothesis_confidence >= 0 and "
            "analysis_hypothesis_confidence <= 1)",
            name="chart_screenshot_runs_hypothesis_confidence_range",
        ),
        CheckConstraint(
            "raw_candle_count >= 0",
            name="chart_screenshot_runs_raw_count_non_negative",
        ),
        CheckConstraint(
            "stored_candle_count >= 0",
            name="chart_screenshot_runs_stored_count_non_negative",
        ),
        CheckConstraint(
            "duplicate_count >= 0",
            name="chart_screenshot_runs_duplicate_count_non_negative",
        ),
        CheckConstraint(
            "conflict_count >= 0",
            name="chart_screenshot_runs_conflict_count_non_negative",
        ),
        Index("ix_chart_screenshot_runs_workspace_id", "workspace_id"),
        Index("ix_chart_screenshot_runs_workspace_source", "workspace_id", "source_id"),
        Index("ix_chart_screenshot_runs_symbol_timeframe", "symbol_id", "timeframe"),
        Index("ix_chart_screenshot_runs_analysis_run_id", "analysis_run_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parser_name: Mapped[str] = mapped_column(String(80), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    parser_source_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    extraction_confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        server_default=text("0"),
    )
    raw_candle_count: Mapped[int] = mapped_column(
        nullable=False,
        server_default=text("0"),
    )
    stored_candle_count: Mapped[int] = mapped_column(
        nullable=False,
        server_default=text("0"),
    )
    duplicate_count: Mapped[int] = mapped_column(
        nullable=False,
        server_default=text("0"),
    )
    conflict_count: Mapped[int] = mapped_column(
        nullable=False,
        server_default=text("0"),
    )
    analysis_hypothesis: Mapped[str] = mapped_column(String(16), nullable=False)
    analysis_hypothesis_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    extracted_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    extracted_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    extracted_payload_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    extraction_warnings_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    parser_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def chart_type(self) -> str | None:
        value = self.parser_metadata_json.get("chartType")
        return str(value) if value is not None else None

    @property
    def supported_for_analysis(self) -> bool | None:
        value = self.parser_metadata_json.get("supportedForAnalysis")
        return value if isinstance(value, bool) else None

    @property
    def ocr_status(self) -> str | None:
        ocr_json = self.parser_metadata_json.get("ocr")
        if not isinstance(ocr_json, dict):
            return None
        value = ocr_json.get("status")
        return str(value) if value is not None else None

    @property
    def ocr_confidence(self) -> Decimal | None:
        ocr_json = self.parser_metadata_json.get("ocr")
        if not isinstance(ocr_json, dict):
            return None
        value = ocr_json.get("confidence")
        if value is None:
            return None
        return Decimal(str(value))

    @property
    def axis_calibration_json(self) -> dict[str, object] | None:
        value = self.parser_metadata_json.get("axisCalibration")
        return value if isinstance(value, dict) else None

    @property
    def analysis_blocked_reason(self) -> str | None:
        value = self.parser_metadata_json.get("analysisBlockedReason")
        return str(value) if value is not None else None
