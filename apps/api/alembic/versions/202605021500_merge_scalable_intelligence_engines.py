"""merge scalable intelligence engines

Revision ID: 202605021500_scalable_engines_merge
Revises: 202605021200_timeframe_aggregation, 202605020900_profile_governance, 202605021330_provider_polling, 202605021300_scenario_ensembles, 202605020900_backtest_experiments
Create Date: 2026-05-02 15:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202605021500_scalable_engines_merge"
down_revision: str | tuple[str, ...] | None = (
    "202605021200_timeframe_aggregation",
    "202605020900_profile_governance",
    "202605021330_provider_polling",
    "202605021300_scenario_ensembles",
    "202605020900_backtest_experiments",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
