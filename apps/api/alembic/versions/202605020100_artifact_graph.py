"""add intelligence artifact graph

Revision ID: 202605020120_artifact_graph
Revises: f9eb9423c4a2
Create Date: 2026-05-02 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605020120_artifact_graph"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intelligence_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("artifact_id", sa.String(length=128), nullable=False),
        sa.Column("artifact_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version_label", sa.String(length=80), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "artifact_type in ('candle_set', 'analysis_run', 'feature_snapshot', "
            "'indicator_snapshot', 'pattern_candidate_set', 'signal', "
            "'deterministic_explanation', 'llm_explanation', 'news_correlation_set', "
            "'outcome_set', 'reasoning_run', 'action_plan', 'report', 'dataset_export', "
            "'quality_run', 'diagnostic_run', 'historical_case_vector', 'rule_manifest', "
            "'chart_screenshot_run', 'replay_run')",
            name="ck_intelligence_artifacts_intelligence_artifact_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('current', 'stale', 'superseded', 'archived', 'unknown')",
            name="ck_intelligence_artifacts_intelligence_artifact_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_intelligence_artifacts_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_intelligence_artifacts"),
        sa.UniqueConstraint(
            "workspace_id",
            "artifact_type",
            "artifact_id",
            name="uq_intelligence_artifacts_workspace_type_artifact",
        ),
    )
    op.create_index(
        "ix_intelligence_artifacts_artifact_key",
        "intelligence_artifacts",
        ["artifact_key"],
        unique=False,
    )
    op.create_index(
        "ix_intelligence_artifacts_status",
        "intelligence_artifacts",
        ["workspace_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_intelligence_artifacts_workspace_id",
        "intelligence_artifacts",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "intelligence_artifact_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_artifact_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_artifact_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column("dependency_version", sa.String(length=32), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "relationship_type in ('produced', 'derived_from', 'explained_by', "
            "'evaluated_by', 'correlated_with', 'reasoned_from', 'planned_from', "
            "'replayed_from', 'corrected_from', 'diagnosed_by', 'exported_from')",
            name=(
                "ck_intelligence_artifact_dependencies_"
                "intelligence_artifact_dependency_relationship_allowed"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["source_artifact_record_id"],
            ["intelligence_artifacts.id"],
            name=(
                "fk_intelligence_artifact_dependencies_"
                "source_artifact_record_id_intelligence_artifacts"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_artifact_record_id"],
            ["intelligence_artifacts.id"],
            name=(
                "fk_intelligence_artifact_dependencies_"
                "target_artifact_record_id_intelligence_artifacts"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_intelligence_artifact_dependencies_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_intelligence_artifact_dependencies"),
        sa.UniqueConstraint(
            "workspace_id",
            "source_artifact_record_id",
            "target_artifact_record_id",
            "relationship_type",
            name="uq_intelligence_artifact_dependencies_edge",
        ),
    )
    op.create_index(
        "ix_intelligence_artifact_dependencies_source",
        "intelligence_artifact_dependencies",
        ["source_artifact_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_intelligence_artifact_dependencies_target",
        "intelligence_artifact_dependencies",
        ["target_artifact_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_intelligence_artifact_dependencies_workspace_relationship",
        "intelligence_artifact_dependencies",
        ["workspace_id", "relationship_type"],
        unique=False,
    )

    op.create_table(
        "artifact_invalidation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_artifact_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("invalidated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reason_code in ('source_data_changed', 'rule_pack_changed', "
            "'strategy_profile_changed', 'correction_accepted', 'replay_requested', "
            "'manual_invalidation', 'data_quality_changed', 'parser_version_changed')",
            name="ck_artifact_invalidation_events_artifact_invalidation_event_reason_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["source_artifact_record_id"],
            ["intelligence_artifacts.id"],
            name=(
                "fk_artifact_invalidation_events_"
                "source_artifact_record_id_intelligence_artifacts"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_artifact_invalidation_events_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_artifact_invalidation_events"),
    )
    op.create_index(
        "ix_artifact_invalidation_events_source",
        "artifact_invalidation_events",
        ["source_artifact_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_artifact_invalidation_events_workspace_id",
        "artifact_invalidation_events",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "artifact_invalidation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invalidation_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=False),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column(
            "path_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["artifact_record_id"],
            ["intelligence_artifacts.id"],
            name="fk_artifact_invalidation_items_artifact_record_id_intelligence_artifacts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invalidation_event_id"],
            ["artifact_invalidation_events.id"],
            name=(
                "fk_artifact_invalidation_items_"
                "invalidation_event_id_artifact_invalidation_events"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_artifact_invalidation_items_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_artifact_invalidation_items"),
    )
    op.create_index(
        "ix_artifact_invalidation_items_artifact",
        "artifact_invalidation_items",
        ["artifact_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_artifact_invalidation_items_event",
        "artifact_invalidation_items",
        ["invalidation_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_artifact_invalidation_items_event",
        table_name="artifact_invalidation_items",
    )
    op.drop_index(
        "ix_artifact_invalidation_items_artifact",
        table_name="artifact_invalidation_items",
    )
    op.drop_table("artifact_invalidation_items")
    op.drop_index(
        "ix_artifact_invalidation_events_workspace_id",
        table_name="artifact_invalidation_events",
    )
    op.drop_index(
        "ix_artifact_invalidation_events_source",
        table_name="artifact_invalidation_events",
    )
    op.drop_table("artifact_invalidation_events")
    op.drop_index(
        "ix_intelligence_artifact_dependencies_workspace_relationship",
        table_name="intelligence_artifact_dependencies",
    )
    op.drop_index(
        "ix_intelligence_artifact_dependencies_target",
        table_name="intelligence_artifact_dependencies",
    )
    op.drop_index(
        "ix_intelligence_artifact_dependencies_source",
        table_name="intelligence_artifact_dependencies",
    )
    op.drop_table("intelligence_artifact_dependencies")
    op.drop_index("ix_intelligence_artifacts_workspace_id", table_name="intelligence_artifacts")
    op.drop_index("ix_intelligence_artifacts_status", table_name="intelligence_artifacts")
    op.drop_index("ix_intelligence_artifacts_artifact_key", table_name="intelligence_artifacts")
    op.drop_table("intelligence_artifacts")
