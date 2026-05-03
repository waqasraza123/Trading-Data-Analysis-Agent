from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class DataSourceType(StrEnum):
    CSV_UPLOAD = "csv_upload"
    JSON_IMPORT = "json_import"
    API_POLLING = "api_polling"
    WEBSOCKET_LIVE = "websocket_live"
    MANUAL_SEED = "manual_seed"
    CHART_SCREENSHOT = "chart_screenshot"
    DERIVED_AGGREGATION = "derived_aggregation"


class DataSourceStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type in ('csv_upload', 'json_import', 'api_polling', "
            "'websocket_live', 'manual_seed', 'chart_screenshot', 'derived_aggregation')",
            name="source_type_allowed",
        ),
        CheckConstraint("status in ('active', 'inactive', 'failed')", name="status_allowed"),
        Index("ix_data_sources_workspace_id", "workspace_id"),
        Index("ix_data_sources_source_type", "source_type"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
