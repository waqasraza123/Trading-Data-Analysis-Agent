"""harden chart screenshot parsing

Revision ID: 202604301900
Revises: 202604301800
Create Date: 2026-04-30 19:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202604301900"
down_revision: str | Sequence[str] | None = "202604301800"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


STATUS_CONSTRAINT = "ck_chart_screenshot_runs_chart_screenshot_runs_status_allowed"


def upgrade() -> None:
    op.drop_constraint(STATUS_CONSTRAINT, "chart_screenshot_runs", type_="check")
    op.create_check_constraint(
        STATUS_CONSTRAINT,
        "chart_screenshot_runs",
        "status in ('received', 'parsing', 'ingested', 'review_required', "
        "'analysis_triggered', 'analysis_failed', 'failed', 'completed')",
    )


def downgrade() -> None:
    op.execute(
        "update chart_screenshot_runs set status = 'completed' where status = 'review_required'"
    )
    op.drop_constraint(STATUS_CONSTRAINT, "chart_screenshot_runs", type_="check")
    op.create_check_constraint(
        STATUS_CONSTRAINT,
        "chart_screenshot_runs",
        "status in ('received', 'parsing', 'ingested', 'analysis_triggered', "
        "'analysis_failed', 'failed', 'completed')",
    )
