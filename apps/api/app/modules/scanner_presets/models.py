from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ScannerPresetCategory(StrEnum):
    SESSION = "session"
    MARKET = "market"
    VOLATILITY = "volatility"
    PATTERN_CONTEXT = "pattern_context"
    DATA_REPAIR = "data_repair"
    REVIEW = "review"


class ScannerPresetStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ScannerPresetApplicationStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class ScannerPreset(Base):
    __tablename__ = "scanner_presets"
    __table_args__ = (
        CheckConstraint(
            "category in ('session', 'market', 'volatility', 'pattern_context', "
            "'data_repair', 'review')",
            name="scanner_presets_category_allowed",
        ),
        CheckConstraint(
            "status in ('active', 'archived')",
            name="scanner_presets_status_allowed",
        ),
        Index("ix_scanner_presets_key_version", "key", "preset_version"),
        Index("ix_scanner_presets_category_status", "category", "status"),
        Index("ix_scanner_presets_workspace_key", "workspace_id", "key"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    key: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    preset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    market_types_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    symbol_templates_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    timeframe_templates_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    session_filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    scan_config_template_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    watchlist_template_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    preference_profile_filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class ScannerPresetApplication(Base):
    __tablename__ = "scanner_preset_applications"
    __table_args__ = (
        CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="scanner_preset_applications_status_allowed",
        ),
        Index(
            "ix_scanner_preset_applications_workspace_preset",
            "workspace_id",
            "scanner_preset_id",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    scanner_preset_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("scanner_presets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    watchlist_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("market_watchlists.id", ondelete="SET NULL"),
        nullable=True,
    )
    scan_config_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("scheduled_scan_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    preference_profile_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("personal_strategy_preference_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    applied_config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
