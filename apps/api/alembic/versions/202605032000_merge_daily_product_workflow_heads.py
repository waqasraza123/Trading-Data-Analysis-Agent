"""merge daily product workflow heads

Revision ID: 202605032000_daily_product_workflow_merge
Revises: 202605031900_daily_briefs, 202605031900_daily_workflow_runs, 202605031900_scanner_presets
Create Date: 2026-05-03 20:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202605032000_daily_product_workflow_merge"
down_revision: str | Sequence[str] | None = (
    "202605031900_daily_briefs",
    "202605031900_daily_workflow_runs",
    "202605031900_scanner_presets",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
