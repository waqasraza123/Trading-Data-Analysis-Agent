from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class IntelligenceCatalogArtifactType(StrEnum):
    ANALYSIS_RUN = "analysis_run"
    SIGNAL = "signal"
    OUTCOME = "outcome"
    REASONING_RUN = "reasoning_run"
    ACTION_PLAN = "action_plan"
    ACTION_ITEM = "action_item"
    NEWS_EVENT = "news_event"
    CHART_SCREENSHOT_RUN = "chart_screenshot_run"
    OPERATOR_REVIEW = "operator_review"
    QUALITY_RUN = "quality_run"
    DIAGNOSTIC_RUN = "diagnostic_run"
    DATASET_EXPORT = "dataset_export"
    REPORT = "report"
    RULE_MANIFEST = "rule_manifest"
    PROVIDER_POLLING_REQUEST = "provider_polling_request"
    SCHEDULED_SCAN_RUN = "scheduled_scan_run"


class IntelligenceCatalogItem(Base):
    __tablename__ = "intelligence_catalog_items"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "artifact_type",
            "artifact_id",
            name="uq_intelligence_catalog_items_workspace_artifact",
        ),
        Index(
            "ix_intelligence_catalog_items_workspace_artifact_type", "workspace_id", "artifact_type"
        ),
        Index("ix_intelligence_catalog_items_workspace_status", "workspace_id", "status"),
        Index(
            "ix_intelligence_catalog_items_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
        ),
        Index(
            "ix_intelligence_catalog_items_workspace_strategy_profile",
            "workspace_id",
            "strategy_profile_key",
        ),
        Index(
            "ix_intelligence_catalog_items_workspace_pattern_type", "workspace_id", "pattern_type"
        ),
        Index("ix_intelligence_catalog_items_workspace_bias", "workspace_id", "bias"),
        Index(
            "ix_intelligence_catalog_items_workspace_outcome_label", "workspace_id", "outcome_label"
        ),
        Index("ix_intelligence_catalog_items_workspace_indexed_at", "workspace_id", "indexed_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    strategy_profile_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pattern_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    bias: Mapped[str | None] = mapped_column(String(32), nullable=True)
    classification_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quality_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    readiness_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    searchable_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    artifact_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = created_at_column()
    updated_at = updated_at_column()
