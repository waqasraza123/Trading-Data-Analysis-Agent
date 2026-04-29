"""merge live runtime and analysis snapshots

Revision ID: f9eb9423c4a2
Revises: 202604291230, 202604291240
Create Date: 2026-04-29 16:47:38.427986
"""

from collections.abc import Sequence

revision: str = "f9eb9423c4a2"
down_revision: str | tuple[str, str] | None = ("202604291230", "202604291240")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
