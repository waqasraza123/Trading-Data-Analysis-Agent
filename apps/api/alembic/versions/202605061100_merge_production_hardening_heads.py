"""merge production hardening heads

Revision ID: 202605061100_production_hardening_merge
Revises:
    202605061000_auth_identity_api_keys
    202605061000_candle_ingestion_performance
    202605061000_job_queue
    202605061000_service_slo_snapshots
Create Date: 2026-05-06 11:00:00.000000
"""

from collections.abc import Sequence

revision: str = "202605061100_production_hardening_merge"
down_revision: str | Sequence[str] | None = (
    "202605061000_auth_identity_api_keys",
    "202605061000_candle_ingestion_performance",
    "202605061000_job_queue",
    "202605061000_service_slo_snapshots",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
