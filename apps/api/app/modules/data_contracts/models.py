from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class DataContractStatus(StrEnum):
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class DataContractValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"


class DataContract(Base):
    __tablename__ = "data_contracts"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'draft', 'deprecated', 'archived')",
            name="data_contracts_status_allowed",
        ),
        UniqueConstraint("key", "version", name="uq_data_contracts_key_version"),
        Index("ix_data_contracts_key_version_status", "key", "version", "status"),
    )

    id = uuid_primary_key()
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    schema_json: Mapped[dict[str, object]] = mapped_column(
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


class DataContractValidation(Base):
    __tablename__ = "data_contract_validations"
    __table_args__ = (
        CheckConstraint(
            "status in ('passed', 'failed', 'passed_with_warnings')",
            name="data_contract_validations_status_allowed",
        ),
        Index(
            "ix_data_contract_validations_source_type_source_id",
            "source_type",
            "source_id",
        ),
        Index(
            "ix_data_contract_validations_contract_status",
            "contract_key",
            "contract_version",
            "status",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    contract_key: Mapped[str] = mapped_column(String(120), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_errors_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    validation_warnings_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    payload_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
