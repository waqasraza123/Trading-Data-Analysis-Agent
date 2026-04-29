from sqlalchemy import Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, uuid_primary_key


class EngineVersion(Base):
    __tablename__ = "engine_versions"
    __table_args__ = (
        UniqueConstraint("engine_name", "version", name="uq_engine_versions_engine_version"),
        Index("ix_engine_versions_engine_name", "engine_name"),
    )

    id = uuid_primary_key()
    engine_name: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
