"""merge daily workflow heads

Revision ID: 202605031800_merge_daily_workflow_heads
Revises: 202605031700_provider_health_snapshots,
202605031700_signal_priority_scores, 202605031700_preference_profiles
Create Date: 2026-05-03 18:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202605031800_merge_daily_workflow_heads"
down_revision: str | Sequence[str] | None = (
    "202605031700_provider_health_snapshots",
    "202605031700_signal_priority_scores",
    "202605031700_preference_profiles",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
