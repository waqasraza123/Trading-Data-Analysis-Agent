"""add rule packs and reproducibility manifests

Revision ID: 202605020970_rule_packs_reproducibility
Revises: f9eb9423c4a2
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020970_rule_packs_reproducibility"
down_revision: str | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rule_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "engine_versions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "strategy_profile_refs_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "parser_versions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "threshold_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "module_versions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "compatibility_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status in ('draft', 'active', 'deprecated', 'archived')",
            name=op.f("ck_rule_packs_rule_pack_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_rule_packs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_packs")),
    )
    op.create_index(
        "ix_rule_packs_key_version_status",
        "rule_packs",
        ["key", "version", "status"],
        unique=False,
    )
    op.create_index(
        "uq_rule_packs_global_key_version",
        "rule_packs",
        ["key", "version"],
        unique=True,
        postgresql_where=sa.text("workspace_id IS NULL"),
    )
    op.create_index(
        "uq_rule_packs_workspace_key_version",
        "rule_packs",
        ["workspace_id", "key", "version"],
        unique=True,
        postgresql_where=sa.text("workspace_id IS NOT NULL"),
    )
    op.create_table(
        "analysis_reproducibility_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_pack_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("manifest_version", sa.String(length=64), nullable=False),
        sa.Column(
            "engine_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "strategy_profile_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "parser_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "module_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "data_source_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "candle_policy_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("replay_support_status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.String(length=1200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "replay_support_status in ('supported', 'partially_supported', "
            "'unsupported', 'unknown')",
            name=op.f("ck_analysis_reproducibility_manifests_replay_support_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_analysis_reproducibility_manifests_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_pack_id"],
            ["rule_packs.id"],
            name=op.f("fk_analysis_reproducibility_manifests_rule_pack_id_rule_packs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_analysis_reproducibility_manifests_signal_id_signals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_analysis_reproducibility_manifests_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_reproducibility_manifests")),
        sa.UniqueConstraint(
            "analysis_run_id",
            "manifest_version",
            name=op.f("uq_analysis_reproducibility_manifest_run_version"),
        ),
    )
    op.create_index(
        "ix_analysis_reproducibility_manifests_analysis_run_id",
        "analysis_reproducibility_manifests",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_reproducibility_manifests_rule_pack_id",
        "analysis_reproducibility_manifests",
        ["rule_pack_id"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_reproducibility_manifests_signal_id",
        "analysis_reproducibility_manifests",
        ["signal_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analysis_reproducibility_manifests_signal_id",
        table_name="analysis_reproducibility_manifests",
    )
    op.drop_index(
        "ix_analysis_reproducibility_manifests_rule_pack_id",
        table_name="analysis_reproducibility_manifests",
    )
    op.drop_index(
        "ix_analysis_reproducibility_manifests_analysis_run_id",
        table_name="analysis_reproducibility_manifests",
    )
    op.drop_table("analysis_reproducibility_manifests")
    op.drop_index("uq_rule_packs_workspace_key_version", table_name="rule_packs")
    op.drop_index("uq_rule_packs_global_key_version", table_name="rule_packs")
    op.drop_index("ix_rule_packs_key_version_status", table_name="rule_packs")
    op.drop_table("rule_packs")
