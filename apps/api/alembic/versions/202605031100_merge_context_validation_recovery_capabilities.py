"""merge context validation recovery capabilities and safety policy

Revision ID: 202605031100_context_validation_recovery_merge
Revises: current context, validation, recovery, capability, and safety heads
Create Date: 2026-05-03 11:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202605031100_context_validation_recovery_merge"
down_revision: str | Sequence[str] | None = (
    "202605031000_cross_asset_context",
    "202605031000_walk_forward_validation",
    "202605031000_candle_gap_recovery",
    "202605031000_explanation_comparison",
    "202605031000_intelligence_capabilities",
    "20260502_0001",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
