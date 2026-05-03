from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class CapabilityCategory(StrEnum):
    INGESTION = "ingestion"
    ANALYSIS = "analysis"
    SIGNAL = "signal"
    EXPLANATION = "explanation"
    REASONING = "reasoning"
    OUTCOME = "outcome"
    DIAGNOSTICS = "diagnostics"
    REPORTING = "reporting"
    OPERATIONS = "operations"
    SAFETY = "safety"
    GOVERNANCE = "governance"
    EXPORT = "export"


class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class CapabilityExecutionType(StrEnum):
    READ_ONLY = "read_only"
    DETERMINISTIC_WRITE = "deterministic_write"
    EXTERNAL_PROVIDER = "external_provider"
    LLM_PROVIDER = "llm_provider"
    WORKER = "worker"
    MANUAL_ONLY = "manual_only"


class CapabilitySafetyLevel(StrEnum):
    SAFE_READ = "safe_read"
    SAFE_BACKEND_WRITE = "safe_backend_write"
    PROVIDER_BACKED = "provider_backed"
    REVIEW_REQUIRED = "review_required"
    RESTRICTED = "restricted"


class IntelligenceCapability(Base):
    __tablename__ = "intelligence_capabilities"
    __table_args__ = (
        CheckConstraint(
            "category in ('ingestion', 'analysis', 'signal', 'explanation', 'reasoning', "
            "'outcome', 'diagnostics', 'reporting', 'operations', 'safety', 'governance', "
            "'export')",
            name="intelligence_capabilities_category_allowed",
        ),
        CheckConstraint(
            "status in ('available', 'unavailable', 'disabled', 'experimental', 'deprecated')",
            name="intelligence_capabilities_status_allowed",
        ),
        CheckConstraint(
            "execution_type in ('read_only', 'deterministic_write', 'external_provider', "
            "'llm_provider', 'worker', 'manual_only')",
            name="intelligence_capabilities_execution_type_allowed",
        ),
        CheckConstraint(
            "safety_level in ('safe_read', 'safe_backend_write', 'provider_backed', "
            "'review_required', 'restricted')",
            name="intelligence_capabilities_safety_level_allowed",
        ),
        UniqueConstraint("key", "version", name="uq_intelligence_capabilities_key_version"),
        Index("ix_intelligence_capabilities_category_status", "category", "status"),
        Index("ix_intelligence_capabilities_execution_type", "execution_type"),
        Index("ix_intelligence_capabilities_safety_level", "safety_level"),
    )

    id = uuid_primary_key()
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_type: Mapped[str] = mapped_column(String(40), nullable=False)
    safety_level: Mapped[str] = mapped_column(String(40), nullable=False)
    requires_external_credentials: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requires_database: Mapped[bool] = mapped_column(Boolean, nullable=False)
    input_contracts_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    output_contracts_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    produced_artifacts_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    route_refs_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    dependencies_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
