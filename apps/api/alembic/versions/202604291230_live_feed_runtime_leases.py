"""add live feed runtime leases

Revision ID: 202604291230
Revises: 202604291200
Create Date: 2026-04-29 12:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202604291230"
down_revision: str | None = "202604291200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "live_feed_subscriptions",
        sa.Column("worker_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "live_feed_subscriptions",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_live_feed_subscriptions_lease",
        "live_feed_subscriptions",
        ["worker_id", "lease_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_live_feed_subscriptions_lease", table_name="live_feed_subscriptions")
    op.drop_column("live_feed_subscriptions", "lease_expires_at")
    op.drop_column("live_feed_subscriptions", "worker_id")
