"""merge intelligence quality and market scan heads

Revision ID: 202604302200
Revises: 202604302000, 202604302100
Create Date: 2026-04-30 22:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202604302200"
down_revision: str | Sequence[str] | None = ("202604302000", "202604302100")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
