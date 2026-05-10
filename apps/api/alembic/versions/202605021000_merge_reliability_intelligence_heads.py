"""merge reliability intelligence module heads

Revision ID: 202605021000
Revises: 202605020900_advanced_feature_snapshots, 202605020910_backfill_plans,
202605020920_data_contract_registry, 202605020930_data_quality_runs,
202605020940_data_retention_policies, 202605020950_event_study_runs,
202605020960_market_regime_contexts, 202605020970_rule_packs_reproducibility,
202605020980_state_machine_registry
Create Date: 2026-05-02 10:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202605021000"
down_revision: str | Sequence[str] | None = (
    "202605020900_advanced_feature_snapshots",
    "202605020910_backfill_plans",
    "202605020920_data_contract_registry",
    "202605020930_data_quality_runs",
    "202605020940_data_retention_policies",
    "202605020950_event_study_runs",
    "202605020960_market_regime_contexts",
    "202605020970_rule_packs_reproducibility",
    "202605020980_state_machine_registry",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
