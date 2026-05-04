"""merge market memory drift attribution and scenario outcome heads

Revision ID: 202605031300_market_memory_drift_attribution_scenario_merge
Revises: market memory, cohort drift, pattern attribution, scenario outcomes
Create Date: 2026-05-03 13:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202605031300_market_memory_drift_attribution_scenario_merge"
down_revision: str | Sequence[str] | None = (
    "202605031200_market_memory",
    "202605031200_cohort_drift",
    "202605031200_pattern_attribution",
    "202605031200_scenario_hypothesis_outcomes",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
