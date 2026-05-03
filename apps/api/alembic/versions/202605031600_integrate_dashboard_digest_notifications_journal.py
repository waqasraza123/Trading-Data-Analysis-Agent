"""integrate dashboard digest notifications and journal

Revision ID: 202605031600_dashboard_digest_notifications_journal
Revises: 202605031500_setup_contexts
Create Date: 2026-05-03 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031600_dashboard_digest_notifications_journal"
down_revision: str | Sequence[str] | None = "202605031500_setup_contexts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "signal_digest_items",
        sa.Column("setup_context_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_signal_digest_items_setup_context_id_setup_contexts",
        "signal_digest_items",
        "setup_contexts",
        ["setup_context_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_signal_digest_items_setup_context_id",
        "signal_digest_items",
        ["setup_context_id"],
    )
    op.create_foreign_key(
        "fk_journal_entries_setup_context_id_setup_contexts",
        "journal_entries",
        "setup_contexts",
        ["setup_context_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_journal_entries_setup_context_id",
        "journal_entries",
        ["setup_context_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_journal_entries_setup_context_id", table_name="journal_entries")
    op.drop_constraint(
        "fk_journal_entries_setup_context_id_setup_contexts",
        "journal_entries",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_signal_digest_items_setup_context_id",
        table_name="signal_digest_items",
    )
    op.drop_constraint(
        "fk_signal_digest_items_setup_context_id_setup_contexts",
        "signal_digest_items",
        type_="foreignkey",
    )
    op.drop_column("signal_digest_items", "setup_context_id")
