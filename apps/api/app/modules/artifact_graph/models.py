from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ArtifactType(StrEnum):
    CANDLE_SET = "candle_set"
    ANALYSIS_RUN = "analysis_run"
    FEATURE_SNAPSHOT = "feature_snapshot"
    INDICATOR_SNAPSHOT = "indicator_snapshot"
    PATTERN_CANDIDATE_SET = "pattern_candidate_set"
    SIGNAL = "signal"
    DETERMINISTIC_EXPLANATION = "deterministic_explanation"
    LLM_EXPLANATION = "llm_explanation"
    NEWS_CORRELATION_SET = "news_correlation_set"
    OUTCOME_SET = "outcome_set"
    REASONING_RUN = "reasoning_run"
    ACTION_PLAN = "action_plan"
    REPORT = "report"
    DATASET_EXPORT = "dataset_export"
    QUALITY_RUN = "quality_run"
    DIAGNOSTIC_RUN = "diagnostic_run"
    HISTORICAL_CASE_VECTOR = "historical_case_vector"
    RULE_MANIFEST = "rule_manifest"
    CHART_SCREENSHOT_RUN = "chart_screenshot_run"
    REPLAY_RUN = "replay_run"


class ArtifactStatus(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    UNKNOWN = "unknown"


class ArtifactRelationshipType(StrEnum):
    PRODUCED = "produced"
    DERIVED_FROM = "derived_from"
    EXPLAINED_BY = "explained_by"
    EVALUATED_BY = "evaluated_by"
    CORRELATED_WITH = "correlated_with"
    REASONED_FROM = "reasoned_from"
    PLANNED_FROM = "planned_from"
    REPLAYED_FROM = "replayed_from"
    CORRECTED_FROM = "corrected_from"
    DIAGNOSED_BY = "diagnosed_by"
    EXPORTED_FROM = "exported_from"


class ArtifactInvalidationReasonCode(StrEnum):
    SOURCE_DATA_CHANGED = "source_data_changed"
    RULE_PACK_CHANGED = "rule_pack_changed"
    STRATEGY_PROFILE_CHANGED = "strategy_profile_changed"
    CORRECTION_ACCEPTED = "correction_accepted"
    REPLAY_REQUESTED = "replay_requested"
    MANUAL_INVALIDATION = "manual_invalidation"
    DATA_QUALITY_CHANGED = "data_quality_changed"
    PARSER_VERSION_CHANGED = "parser_version_changed"


ARTIFACT_TYPE_VALUES = "', '".join(item.value for item in ArtifactType)
ARTIFACT_STATUS_VALUES = "', '".join(item.value for item in ArtifactStatus)
ARTIFACT_RELATIONSHIP_TYPE_VALUES = "', '".join(
    item.value for item in ArtifactRelationshipType
)
ARTIFACT_INVALIDATION_REASON_CODE_VALUES = "', '".join(
    item.value for item in ArtifactInvalidationReasonCode
)


class IntelligenceArtifact(Base):
    __tablename__ = "intelligence_artifacts"
    __table_args__ = (
        CheckConstraint(
            f"artifact_type in ('{ARTIFACT_TYPE_VALUES}')",
            name="intelligence_artifact_type_allowed",
        ),
        CheckConstraint(
            f"status in ('{ARTIFACT_STATUS_VALUES}')",
            name="intelligence_artifact_status_allowed",
        ),
        UniqueConstraint(
            "workspace_id",
            "artifact_type",
            "artifact_id",
            name="uq_intelligence_artifacts_workspace_type_artifact",
        ),
        Index("ix_intelligence_artifacts_workspace_id", "workspace_id"),
        Index("ix_intelligence_artifacts_artifact_key", "artifact_key"),
        Index("ix_intelligence_artifacts_status", "workspace_id", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_id: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    version_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class IntelligenceArtifactDependency(Base):
    __tablename__ = "intelligence_artifact_dependencies"
    __table_args__ = (
        CheckConstraint(
            f"relationship_type in ('{ARTIFACT_RELATIONSHIP_TYPE_VALUES}')",
            name="intelligence_artifact_dependency_relationship_allowed",
        ),
        UniqueConstraint(
            "workspace_id",
            "source_artifact_record_id",
            "target_artifact_record_id",
            "relationship_type",
            name="uq_intelligence_artifact_dependencies_edge",
        ),
        Index(
            "ix_intelligence_artifact_dependencies_source",
            "source_artifact_record_id",
        ),
        Index(
            "ix_intelligence_artifact_dependencies_target",
            "target_artifact_record_id",
        ),
        Index(
            "ix_intelligence_artifact_dependencies_workspace_relationship",
            "workspace_id",
            "relationship_type",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_artifact_record_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("intelligence_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_artifact_record_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("intelligence_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    dependency_version: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()


class ArtifactInvalidationEvent(Base):
    __tablename__ = "artifact_invalidation_events"
    __table_args__ = (
        CheckConstraint(
            f"reason_code in ('{ARTIFACT_INVALIDATION_REASON_CODE_VALUES}')",
            name="artifact_invalidation_event_reason_allowed",
        ),
        Index("ix_artifact_invalidation_events_workspace_id", "workspace_id"),
        Index(
            "ix_artifact_invalidation_events_source",
            "source_artifact_record_id",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_artifact_record_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("intelligence_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    invalidated_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()


class ArtifactInvalidationItem(Base):
    __tablename__ = "artifact_invalidation_items"
    __table_args__ = (
        Index(
            "ix_artifact_invalidation_items_event",
            "invalidation_event_id",
        ),
        Index(
            "ix_artifact_invalidation_items_artifact",
            "artifact_record_id",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    invalidation_event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("artifact_invalidation_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_record_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("intelligence_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    path_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    created_at = created_at_column()
