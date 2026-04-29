"""add analysis replay metadata

Revision ID: 202604291130
Revises: 202604291030
Create Date: 2026-04-29 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604291130"
down_revision: str | None = "202604291030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("replayed_from_analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("replay_mode", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_analysis_runs_replayed_from_analysis_run_id_analysis_runs"),
        "analysis_runs",
        "analysis_runs",
        ["replayed_from_analysis_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        op.f("ck_analysis_runs_replay_mode_allowed"),
        "analysis_runs",
        "replay_mode is null or replay_mode in "
        "('latest_engine_version', 'same_engine_version')",
    )
    op.create_index(
        "ix_analysis_runs_replayed_from",
        "analysis_runs",
        ["replayed_from_analysis_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_runs_replayed_from", table_name="analysis_runs")
    op.drop_constraint(
        op.f("ck_analysis_runs_replay_mode_allowed"),
        "analysis_runs",
        type_="check",
    )
    op.drop_constraint(
        op.f("fk_analysis_runs_replayed_from_analysis_run_id_analysis_runs"),
        "analysis_runs",
        type_="foreignkey",
    )
    op.drop_column("analysis_runs", "replay_mode")
    op.drop_column("analysis_runs", "replayed_from_analysis_run_id")
