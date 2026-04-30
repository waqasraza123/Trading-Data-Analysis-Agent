"""merge action worker and profile diagnostics heads

Revision ID: 202604301600
Revises: 202604301500, 202604301530
Create Date: 2026-04-30 16:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202604301600"
down_revision: str | tuple[str, str] | None = ("202604301500", "202604301530")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
