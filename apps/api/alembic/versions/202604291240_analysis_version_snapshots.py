"""add analysis version snapshots

Revision ID: 202604291240
Revises: 202604291200
Create Date: 2026-04-29 12:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604291240"
down_revision: str | None = "202604291200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("engine_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("rule_set_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_runs", "rule_set_snapshot_json")
    op.drop_column("analysis_runs", "engine_snapshot_json")
