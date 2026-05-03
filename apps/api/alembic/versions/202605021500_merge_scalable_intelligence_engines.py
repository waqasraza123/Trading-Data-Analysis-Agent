"""merge scalable intelligence engines

Revision ID: 202605021500_scalable_engines_merge
Revises: 202604302200, 202605020001, 202605020200, 202605021000, 202605021200_timeframe_aggregation, 202605020900_profile_governance, 202605021400, 202605020900_backtest_experiments, 202605021200_historical_case_vectors, 202605021210_intelligence_catalog, 202605021220_operator_playbook_policy_engine, 202605021230_webhook_outbox
Create Date: 2026-05-02 15:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202605021500_scalable_engines_merge"
down_revision: str | tuple[str, ...] | None = (
    "202604302200",
    "202605020001",
    "202605020200",
    "202605021000",
    "202605021200_timeframe_aggregation",
    "202605020900_profile_governance",
    "202605021400",
    "202605020900_backtest_experiments",
    "202605021200_historical_case_vectors",
    "202605021210_intelligence_catalog",
    "202605021220_operator_playbook_policy_engine",
    "202605021230_webhook_outbox",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
