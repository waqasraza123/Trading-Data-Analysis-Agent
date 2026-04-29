from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, uuid_primary_key


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    __table_args__ = (
        Index("ix_feature_snapshots_analysis_run_id", "analysis_run_id"),
        Index(
            "ix_feature_snapshots_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
        ),
        Index("ix_feature_snapshots_window", "start_time", "end_time"),
    )

    id = uuid_primary_key()
    analysis_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    features_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
